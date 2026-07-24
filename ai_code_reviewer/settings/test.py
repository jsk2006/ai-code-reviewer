"""
Settings for running the test suite (`manage.py test --settings=ai_code_reviewer.settings.test`).

Tests shouldn't require Postgres or Redis to actually be running — that's the
whole point of mocking the LLM call and running Celery tasks synchronously.
This module swaps both out for in-process equivalents so `manage.py test` works
standalone, without `docker-compose up` first, in CI or on a fresh clone.
"""

from .dev import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Runs .delay() calls synchronously, in-process, instead of publishing to Redis —
# there's no worker process in the test environment to pick them up otherwise.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']  # faster tests
