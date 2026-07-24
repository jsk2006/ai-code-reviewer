import os

from django.conf import settings
from rest_framework import serializers


def validate_submission_file(uploaded_file):
    """
    Raise a DRF ValidationError (-> 400, not a 500) for files that aren't plausibly
    source code: wrong extension or too large. Called from the create serializer
    so bad uploads are rejected before a Submission row (or Celery job) ever exists.
    """
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in settings.ALLOWED_CODE_FILE_EXTENSIONS:
        raise serializers.ValidationError(
            f'"{uploaded_file.name}" has an unsupported file type ({ext or "no extension"}). '
            f'Allowed: {", ".join(settings.ALLOWED_CODE_FILE_EXTENSIONS)}.'
        )
    if uploaded_file.size > settings.MAX_UPLOAD_FILE_SIZE:
        max_kb = settings.MAX_UPLOAD_FILE_SIZE // 1024
        raise serializers.ValidationError(
            f'"{uploaded_file.name}" is too large ({uploaded_file.size} bytes). Max {max_kb} KB per file.'
        )
