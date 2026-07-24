import logging

from django.conf import settings

from .prompts import build_prompt
from .schemas import ReviewSchema

logger = logging.getLogger(__name__)


def generate_review(category, code_text):
    """
    Returns a plain dict (ReviewSchema.model_dump()), either from the real Gemini
    API or a deterministic mock. Which one runs depends only on whether
    GEMINI_API_KEY is set — nothing else in the codebase (the Celery task, the
    views, the tests) needs to know or care which path ran. That's what makes
    the project runnable end-to-end without a live key.
    """
    if settings.GEMINI_API_KEY:
        review = _call_gemini(category, code_text)
    else:
        logger.info('GEMINI_API_KEY not set - using mock reviewer for category=%s', category)
        review = _mock_review(category, code_text)
    return review.model_dump()


def _call_gemini(category, code_text):
    # Imported lazily so `google-genai` doesn't need to be importable (or a key
    # configured) just to run tests / use the mock path.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = build_prompt(category, code_text)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=ReviewSchema,
            ),
        )
        return ReviewSchema.model_validate_json(response.text)
    except Exception as exc:
        # Re-raised as a plain RuntimeError so the Celery task (tasks.py) has one
        # exception type to catch regardless of whether it's a genai SDK error,
        # a network error, or a schema-validation error from a malformed response.
        raise RuntimeError(f'Gemini review failed: {exc}') from exc


def _mock_review(category, code_text):
    """Cheap, deterministic stand-in used whenever no GEMINI_API_KEY is configured."""
    line_count = len(code_text.splitlines()) or 1
    data = dict(
        overall_score=7,
        summary=(
            f'[MOCK REVIEW] {line_count}-line {category} submission. '
            'Set GEMINI_API_KEY in .env to get a real Gemini review instead of this placeholder.'
        ),
        readability='Mock reviewer - readability was not actually assessed.',
        best_practices='Mock reviewer - best practices were not actually assessed.',
        top_improvements=['Configure GEMINI_API_KEY to receive real feedback.'],
    )
    if category == 'dsa':
        data.update(time_complexity='O(n) [mock]', space_complexity='O(1) [mock]')
    elif category == 'production':
        data.update(security_notes='Not assessed [mock]', scalability_notes='Not assessed [mock]')
    elif category == 'learning':
        data.update(suggested_next_steps=['Add tests [mock]', 'Add docstrings [mock]'])
    return ReviewSchema(**data)
