"""
Local development settings. This is the default settings module (see manage.py,
wsgi.py, asgi.py, and celery.py) — you get this unless DJANGO_SETTINGS_MODULE is
overridden to point at `prod`.
"""

import os

from .base import *  # noqa: F401,F403

# SECURITY WARNING: keep the secret key used in production secret! This insecure
# default is fine for local dev only — prod.py refuses to start without a real one.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')

DEBUG = True

ALLOWED_HOSTS = ['*']
