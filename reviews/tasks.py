import hashlib
import logging

from celery import shared_task
from django.core.cache import cache

from .models import ReviewResult, Submission
from .services import generate_review

logger = logging.getLogger(__name__)

# How long a cached review is reused for. A week is generous but arbitrary —
# code doesn't change meaning over time, so there's no correctness reason to
# expire it sooner; this mostly just bounds how long stale entries linger in
# Redis if the review schema/prompts change and old cached shapes go unused.
REVIEW_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7


def _gather_code_text(submission):
    """
    Combine the raw pasted code with the text of every uploaded file into one
    string to hand the LLM. Each file is prefixed with its name so multi-file
    submissions (e.g. a .py file plus a README) don't get jumbled together.
    """
    parts = []
    if submission.code_content.strip():
        parts.append(submission.code_content)
    for submission_file in submission.files.order_by('id'):
        submission_file.file.open('rb')
        try:
            text = submission_file.file.read().decode('utf-8', errors='replace')
        finally:
            submission_file.file.close()
        parts.append(f'# File: {submission_file.original_name}\n{text}')
    return '\n\n'.join(parts)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_submission(self, submission_id):
    """
    Runs in a Celery worker process — a separate OS process from the one handling
    the HTTP request that created the submission. This is the only place
    Submission.status moves from "pending" to "processing" to "done"/"failed";
    the view that created the submission has already returned a 201 by the time
    this even starts running.
    """
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        # Nothing to retry - the row is gone (e.g. deleted between enqueue and pickup).
        logger.warning('process_submission: submission %s no longer exists', submission_id)
        return

    submission.status = Submission.Status.PROCESSING
    submission.save(update_fields=['status', 'updated_at'])

    try:
        code_text = _gather_code_text(submission)
        # Hash category + code together: the same snippet reviewed as "dsa" vs.
        # "production" should get different feedback, so it needs a different
        # cache entry.
        content_hash = hashlib.sha256(f'{submission.category}\n{code_text}'.encode('utf-8')).hexdigest()
        submission.content_hash = content_hash
        submission.save(update_fields=['content_hash', 'updated_at'])

        cache_key = f'review:{content_hash}'
        review_data = cache.get(cache_key)
        if review_data is None:
            review_data = generate_review(submission.category, code_text)
            cache.set(cache_key, review_data, REVIEW_CACHE_TTL_SECONDS)
        else:
            logger.info('Cache hit for submission %s (hash=%s) - skipped the LLM call', submission_id, content_hash)

        ReviewResult.objects.update_or_create(
            submission=submission,
            defaults={
                'overall_score': review_data.get('overall_score'),
                'summary': review_data.get('summary', ''),
                'structured_review': review_data,
            },
        )
        submission.status = Submission.Status.DONE
        submission.save(update_fields=['status', 'updated_at'])
    except Exception as exc:
        # Anything from a Gemini API failure to a malformed response lands here.
        # We record it on the submission (visible via the status endpoint) rather
        # than letting Celery silently retry forever or the task just vanish.
        logger.exception('Review failed for submission %s', submission_id)
        submission.status = Submission.Status.FAILED
        submission.error_message = str(exc)
        submission.save(update_fields=['status', 'error_message', 'updated_at'])
