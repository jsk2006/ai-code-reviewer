"""
Production-leaning settings. Not wired up by docker-compose (which uses dev.py for
simplicity in this learning project) — included so you can see what actually differs
between "runs on my machine" and "safe to expose on the internet", and switch to it
with DJANGO_SETTINGS_MODULE=ai_code_reviewer.settings.prod when you're ready.
"""

import os

from .base import *  # noqa: F401,F403

# No insecure fallback here: fail loudly at startup rather than silently running
# with a guessable secret key in production.
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = False

ALLOWED_HOSTS = [h for h in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if h]

# HTTPS/security hardening that only makes sense once you're behind a real domain.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
