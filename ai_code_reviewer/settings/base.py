"""
Settings shared by every environment (dev.py and prod.py both import * from here).

Splitting settings this way is a common Django pattern once a project needs to run
in more than one environment (your laptop vs. a Docker container vs. a real server):
`base.py` holds everything that doesn't change, and each environment file overrides
just the handful of things that do (DEBUG, ALLOWED_HOSTS, secret key handling).
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR is ai_code_reviewer/settings/base.py -> parents[2] is the repo root.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load variables from a .env file in the repo root (GEMINI_API_KEY, POSTGRES_*, etc.)
# so we don't have to export them manually in every shell. In Docker, docker-compose's
# `env_file:` does this job instead, but calling load_dotenv() here is harmless if the
# file doesn't exist.
load_dotenv(BASE_DIR / ".env")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'reviews',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ai_code_reviewer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ai_code_reviewer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
#
# Read from environment variables so the same settings work whether Postgres is
# running in Docker (host="db", the service name in docker-compose.yml) or on your
# host machine directly (host="localhost").

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'ai_code_reviewer'),
        'USER': os.getenv('POSTGRES_USER', 'ai_code_reviewer'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'ai_code_reviewer'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static & media files
# MEDIA_ROOT is where uploaded code files (SubmissionFile.file) get written to disk.
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Pagination for list endpoints (the history endpoint, step 7).
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    # Per-user throttling is scoped per-view (see reviews/throttles.py, step 8) rather
    # than applied globally, so we only declare the *rates* here and attach the
    # throttle class to the specific view that needs it.
    'DEFAULT_THROTTLE_RATES': {
        # "submission" rate limits how many code reviews a user can submit per day.
        # Overridable via env var so you can loosen it for local testing.
        'submission': os.getenv('SUBMISSION_THROTTLE_RATE', '20/day'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}


# Celery
# https://docs.celeryq.org/en/stable/userguide/configuration.html
#
# Redis plays two roles in this project: Celery's message broker (how the Django
# process hands off "please review submission #42" jobs to worker processes) and,
# separately, Django's cache backend (step 10, for skipping duplicate LLM calls).
# We use different Redis logical DBs (the trailing /0, /1) so the two uses don't
# collide, even though it's the same Redis server.
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Task results expire after a day so the Redis result backend doesn't grow forever;
# we don't actually rely on the result backend (status lives on the Submission row),
# this just keeps Redis tidy.
CELERY_RESULT_EXPIRES = 86400


# Cache (step 10: identical-code review caching)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_CACHE_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/1'),
    }
}


# Gemini API — read once here so every module that needs it (reviews/services.py)
# imports from settings instead of re-reading the environment.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Maximum size (bytes) accepted for a single uploaded code file, and the file
# extensions we consider "code" (used by the submission serializer, step 4).
MAX_UPLOAD_FILE_SIZE = int(os.getenv('MAX_UPLOAD_FILE_SIZE', str(512 * 1024)))  # 512 KB
ALLOWED_CODE_FILE_EXTENSIONS = [
    '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.cs', '.kt', '.swift', '.sql', '.sh', '.txt', '.md',
]
