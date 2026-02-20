"""
IshemaLink — DEVELOPMENT settings.
Uses SQLite (no Docker needed), DEBUG=True, relaxed security.
DO NOT use in production. Switch to main branch for production settings.
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "dev-insecure-key-change-in-production-do-not-use"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    # "channels",        # TODO: wire up in Phase 8
    "django_filters",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.authentication",
    "apps.shipments",
    "apps.payments",
    "apps.notifications",
    "apps.tracking",
    "apps.govtech",
    "apps.analytics",
    "apps.ops",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ishemalink.urls"
WSGI_APPLICATION = "ishemalink.wsgi.application"
# ASGI_APPLICATION = "ishemalink.asgi.application"  # uncomment in Phase 8

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ── Database: SQLite for dev, no Docker needed ────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Cache: in-memory for dev ──────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# TODO Phase 8: wire up Redis + Channels
# REDIS_URL = "redis://localhost:6379/0"
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {"hosts": [REDIS_URL]},
#     }
# }

# TODO Phase 11: wire up Celery
# CELERY_BROKER_URL = REDIS_URL

AUTH_USER_MODEL = "authentication.Agent"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=24),  # longer in dev for convenience
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # useful in dev/browsable API
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # No throttling in dev
}

SPECTACULAR_SETTINGS = {
    "TITLE": "IshemaLink API (Dev)",
    "DESCRIPTION": "Development build — IshemaLink National Logistics Platform",
    "VERSION": "dev",
}

LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Africa/Kigali"
USE_I18N      = True
USE_TZ        = True

STATIC_URL  = "/static/"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "media"

# Dev: relaxed CORS
CORS_ALLOW_ALL_ORIGINS = True

# Mock external services (all point to localhost stubs)
RRA_EBM_BASE_URL    = "http://localhost:8001"
RURA_API_BASE_URL   = "http://localhost:8002"
SMS_GATEWAY_URL     = "http://localhost:8003"
MTN_MOMO_BASE_URL   = "http://localhost:8004"
AIRTEL_MONEY_BASE_URL = "http://localhost:8005"

MAINTENANCE_MODE = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Dev-only: print emails to console instead of sending
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Dev logging: verbose, human-readable (not JSON)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        }
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
}
