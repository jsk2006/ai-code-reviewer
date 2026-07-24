from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ReviewResult, Submission
from .tasks import process_submission


class AuthFlowTests(APITestCase):
    """Step 2: signup -> login -> use the access token on a protected endpoint."""

    def test_signup_creates_user_with_hashed_password(self):
        response = self.client.post(reverse('api_signup'), {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'a-strong-password-123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='alice')
        # Never stored in plain text - create_user() runs it through Django's hasher.
        self.assertNotEqual(user.password, 'a-strong-password-123')
        self.assertTrue(user.check_password('a-strong-password-123'))

    def test_signup_rejects_duplicate_email(self):
        User.objects.create_user(username='bob', email='dup@example.com', password='whatever-123')
        response = self.client.post(reverse('api_signup'), {
            'username': 'bob2',
            'email': 'dup@example.com',
            'password': 'another-password-123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_then_access_protected_endpoint(self):
        User.objects.create_user(username='carol', email='carol@example.com', password='carol-password-123')

        login_response = self.client.post(reverse('api_login'), {
            'username': 'carol', 'password': 'carol-password-123',
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access_token = login_response.data['access']

        # No credentials -> the global IsAuthenticated default should reject this.
        anon_response = self.client.get(reverse('api_submission_list_create'))
        self.assertEqual(anon_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        authed_response = self.client.get(reverse('api_submission_list_create'))
        self.assertEqual(authed_response.status_code, status.HTTP_200_OK)


class SubmissionCreateTests(APITestCase):
    """Step 4: creating a submission validates input and enqueues a review job."""

    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='dave-password-123')
        self.client.force_authenticate(user=self.user)

    @patch('reviews.views.process_submission')
    def test_create_with_code_content_returns_pending_and_enqueues_task(self, mock_task):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('api_submission_list_create'), {
                'category': Submission.Category.DSA,
                'code_content': 'def two_sum(nums, target):\n    pass\n',
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Submission.Status.PENDING)
        submission_id = response.data['id']
        mock_task.delay.assert_called_once_with(submission_id)

    def test_create_without_code_or_files_is_rejected(self):
        response = self.client.post(reverse('api_submission_list_create'), {
            'category': Submission.Category.LEARNING,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_disallowed_file_extension_is_rejected(self):
        bad_file = SimpleUploadedFile('malware.exe', b'not code', content_type='application/octet-stream')
        response = self.client.post(reverse('api_submission_list_create'), {
            'category': Submission.Category.PRODUCTION,
            'files': [bad_file],
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_only_lists_own_submissions(self):
        other_user = User.objects.create_user(username='eve', password='eve-password-123')
        Submission.objects.create(user=other_user, category=Submission.Category.DSA, code_content='x = 1')
        mine = Submission.objects.create(user=self.user, category=Submission.Category.DSA, code_content='y = 2')

        response = self.client.get(reverse('api_submission_list_create'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data['results']]
        self.assertEqual(ids, [mine.id])

    def test_detail_endpoint_404s_for_other_users_submission(self):
        other_user = User.objects.create_user(username='frank', password='frank-password-123')
        theirs = Submission.objects.create(user=other_user, category=Submission.Category.DSA, code_content='x = 1')

        response = self.client.get(reverse('api_submission_detail', args=[theirs.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ProcessSubmissionTaskTests(APITestCase):
    """
    Step 5/9: the Celery task itself, called directly as a plain function (no
    broker involved) with the Gemini call mocked out, so these tests exercise
    the status transitions and ReviewResult creation without ever touching a
    real LLM or needing Redis running.
    """

    def setUp(self):
        # LocMemCache (settings/test.py) is shared across the whole test run, not
        # reset per-test by default - clear it so the caching test below (and any
        # other test reusing this exact code snippet) doesn't see a stale hit.
        cache.clear()
        self.user = User.objects.create_user(username='grace', password='grace-password-123')
        self.submission = Submission.objects.create(
            user=self.user,
            category=Submission.Category.DSA,
            code_content='def add(a, b):\n    return a + b\n',
        )

    @patch('reviews.tasks.generate_review')
    def test_successful_review_marks_done_and_saves_result(self, mock_generate_review):
        mock_generate_review.return_value = {
            'overall_score': 8,
            'summary': 'Solid, simple implementation.',
            'readability': 'Clear.',
            'best_practices': 'Fine.',
            'top_improvements': ['Add type hints.'],
            'time_complexity': 'O(1)',
            'space_complexity': 'O(1)',
        }

        process_submission(self.submission.id)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.DONE)
        review = ReviewResult.objects.get(submission=self.submission)
        self.assertEqual(review.overall_score, 8)
        self.assertEqual(review.structured_review['time_complexity'], 'O(1)')

    @patch('reviews.tasks.generate_review')
    def test_llm_failure_marks_failed_with_error_message(self, mock_generate_review):
        mock_generate_review.side_effect = RuntimeError('Gemini review failed: quota exceeded')

        process_submission(self.submission.id)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.Status.FAILED)
        self.assertIn('quota exceeded', self.submission.error_message)
        self.assertFalse(ReviewResult.objects.filter(submission=self.submission).exists())

    def test_missing_submission_id_is_a_noop(self):
        # Shouldn't raise - e.g. the row was deleted between enqueue and pickup.
        process_submission(999999)

    @patch('reviews.tasks.generate_review')
    def test_identical_code_reuses_cached_review_and_skips_llm_call(self, mock_generate_review):
        mock_generate_review.return_value = {
            'overall_score': 9, 'summary': 'Cached.', 'readability': '', 'best_practices': '',
            'top_improvements': [],
        }
        other_submission = Submission.objects.create(
            user=self.user,
            category=self.submission.category,
            code_content=self.submission.code_content,  # identical category + code
        )

        process_submission(self.submission.id)
        process_submission(other_submission.id)

        mock_generate_review.assert_called_once()  # second call was served from cache
        self.assertEqual(
            ReviewResult.objects.get(submission=other_submission).summary, 'Cached.'
        )
