"""
Celery application instance for this project.

Celery needs its own "app" object, separate from Django's, that knows how to talk to
the broker (Redis) and how to find task functions. We create it once here and import
it from ai_code_reviewer/__init__.py so that running `celery -A ai_code_reviewer worker`
picks it up automatically.
"""

import os

from celery import Celery

# Celery needs Django's settings loaded before it can read CELERY_* config below,
# so set the settings module before doing anything else — same as manage.py does.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_code_reviewer.settings.dev')

app = Celery('ai_code_reviewer')

# Read CELERY_* settings from Django's settings.py (namespace="CELERY" means we write
# CELERY_BROKER_URL in settings instead of BROKER_URL — keeps Celery config visually
# grouped and grep-able alongside the rest of Django's settings).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover a tasks.py in each app listed in INSTALLED_APPS (reviews/tasks.py).
app.autodiscover_tasks()
