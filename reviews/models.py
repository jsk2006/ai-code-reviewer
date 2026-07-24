from django.conf import settings
from django.db import models


def submission_file_path(instance, filename):
    """Where an uploaded file lands on disk: media/submissions/<user_id>/<submission_id>/<filename>."""
    return f'submissions/{instance.submission.user_id}/{instance.submission_id}/{filename}'


class Submission(models.Model):
    """
    One code review request. A submission can carry raw pasted code, one or more
    uploaded files, or both — at least one is required (enforced in the serializer,
    not here, since "at least one of two optional fields" isn't expressible as a
    single-field model constraint).

    `status` is the state machine the async flow revolves around:
    PENDING (just created, not picked up yet) -> PROCESSING (worker has it) ->
    DONE / FAILED. Clients poll GET /api/submissions/<id>/ and watch this field.
    """

    class Category(models.TextChoices):
        DSA = 'dsa', 'DSA / Competitive Programming'
        PRODUCTION = 'production', 'Production Code'
        LEARNING = 'learning', 'Learning Project'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        DONE = 'done', 'Done'
        FAILED = 'failed', 'Failed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    code_content = models.TextField(
        blank=True,
        help_text='Raw pasted code. Optional if files are attached instead.',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(
        blank=True,
        help_text='Populated when status=failed, e.g. the Gemini API error.',
    )
    # SHA-256 of the reviewed content (code_content + file contents), used by the
    # caching layer (step 10) to detect "we already reviewed this exact code".
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Submission #{self.pk} ({self.category}, {self.status})'


class SubmissionFile(models.Model):
    """One uploaded file attached to a submission (a submission may have several)."""

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=submission_file_path)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name


class ReviewResult(models.Model):
    """
    The LLM's structured feedback for a submission. One-to-one, not a FK, because
    a submission gets reviewed exactly once (re-running would create a new
    Submission, not a second ReviewResult on the same one).
    """

    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='review')
    overall_score = models.IntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)
    # The full structured response (per-category fields differ - see
    # reviews/prompts.py - so we store it as JSON rather than a fixed set of
    # columns).
    structured_review = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review for submission #{self.submission_id}'
