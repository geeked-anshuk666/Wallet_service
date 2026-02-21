"""
settings.py — Django Configuration for the Wallet Service

Environment variables (via python-decouple):
  - SECRET_KEY:     Django secret key. MUST be changed in production.
  - DEBUG:          Set to False in production.
  - DATABASE_URL:   PostgreSQL connection string.
  - ALLOWED_HOSTS:  Comma-separated list of hostnames (e.g., "myapp.onrender.com").
"""

import os
from pathlib import Path

from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ──────────────────────────────────────────────────

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-only-change-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

# Reads comma-separated hosts from env var, defaults to '*' for local dev
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')


# ── Installed Apps ────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',       # API views, content negotiation, serializers
    'drf_spectacular',      # OpenAPI 3.0 schema generation + Swagger UI

    # Project
    'wallets',              # Core wallet app (models, views, services)
]


# ── Middleware ────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serves static files without nginx (needed for Render)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wallet_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wallet_service.wsgi.application'


# ── Database ──────────────────────────────────────────────────
# Uses dj-database-url to parse the DATABASE_URL connection string.
# Defaults to a local PostgreSQL instance for development.

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgresql://wallet_user:wallet_pass@localhost:5432/wallet_db')
    )
}


# ── Cache ─────────────────────────────────────────────────────
# In-memory cache backend — used by django-ratelimit for storing rate counters.
# Each Gunicorn worker gets its own counter. For stricter enforcement, swap to Redis.

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


# ── Auth ──────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Internationalization ─────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ── Static Files ─────────────────────────────────────────────
# Whitenoise serves static files directly from the app process in production.
# collectstatic runs as part of the Dockerfile CMD before Gunicorn starts.

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── Django REST Framework ────────────────────────────────────
# No authentication/permissions required — this is an internal service.
# drf-spectacular auto-generates the OpenAPI schema from @extend_schema decorators.

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [],                           # No auth — open API
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
}


# ── Swagger / OpenAPI Settings ───────────────────────────────
# These control the /docs (Swagger UI) and /redoc endpoints.
# SECURITY: [] removes the lock icon / credentials popup from Swagger UI.

SPECTACULAR_SETTINGS = {
    'TITLE': 'Wallet Service API',
    'DESCRIPTION': (
        'Closed-loop virtual currency wallet with double-entry ledger, idempotency, and rate limiting.\n\n'
        '## Quick Start — Try It Now\n\n'
        'Use these pre-seeded wallet IDs to test the endpoints below:\n\n'
        '| User | Wallet ID | Starting Balance |\n'
        '|------|-----------|------------------|\n'
        '| Alice | `44444444-4444-4444-4444-444444444444` | 500 GLD |\n'
        '| Bob | `55555555-5555-5555-5555-555555555555` | 200 GLD |\n\n'
        '**Asset Type ID** (required for mutations): `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` (Gold Coins)\n\n'
        'Or call **GET /api/v1/wallets** to discover all available wallets dynamically.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,  # Don't embed the raw schema in Swagger UI
    'SECURITY': [],                 # No auth schemes advertised
}


# ── Logging ──────────────────────────────────────────────────
# Routes all 'wallets' logger output to the console (stdout/stderr).
# Critical for seeing audit write failures and service errors in Docker/Render logs.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'wallets': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
