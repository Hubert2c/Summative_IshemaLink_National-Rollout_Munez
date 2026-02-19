"""
IshemaLink – Production-oriented Django settings.
Rwanda data-sovereignty: all data stored in-country (AOS / KtRN cloud).
"""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost 127.0.0.1").split()

# ── Apps ─────────────────────────────────────────────────────────────────────
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
    "channels",
    "django_filters",
    "corsheaders",
    "django_prometheus",
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
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "ishemalink.urls"
WSGI_APPLICATION = "ishemalink.wsgi.application"
ASGI_APPLICATION = "ishemalink.asgi.application"

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

# ── Database (PostgreSQL + PgBouncer) ────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     os.environ.get("DB_NAME",     "ishemalink"),
        "USER":     os.environ.get("DB_USER",     "ishemalink"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "ishemalink"),
        "HOST":     os.environ.get("DB_HOST",     "pgbouncer"),
        "PORT":     os.environ.get("DB_PORT",     "5432"),
        "CONN_MAX_AGE": 0,   # PgBouncer manages pooling
        "OPTIONS":  {"options": "-c default_transaction_isolation=serializable"},
    }
}

# ── Cache / Redis ─────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# ── Channels (WebSocket for live tracking) ────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG":  {"hosts": [REDIS_URL]},
    }
}

# ── Celery (Async tasks: Momo webhooks, EBM signing, SMS) ────────────────────
CELERY_BROKER_URL      = REDIS_URL
CELERY_RESULT_BACKEND  = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT  = ["json"]
CELERY_TIMEZONE        = "Africa/Kigali"

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "authentication.Agent"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "5000/hour",
    },
}

# ── OpenAPI ───────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "IshemaLink API",
    "DESCRIPTION": "National Logistics Platform — Rwanda",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Africa/Kigali"
USE_I18N      = True
USE_TZ        = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "media"

# ── Logging (structured JSON) ─────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django":      {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "ishemalink":  {"handlers": ["console"], "level": "INFO",    "propagate": False},
    },
}

# ── Maintenance mode ──────────────────────────────────────────────────────────
MAINTENANCE_MODE = False

# ── External services ─────────────────────────────────────────────────────────
MTN_MOMO_BASE_URL   = os.environ.get("MTN_MOMO_BASE_URL",   "https://sandbox.momodeveloper.mtn.com")
AIRTEL_MONEY_BASE_URL = os.environ.get("AIRTEL_MONEY_BASE_URL", "https://openapi.airtel.africa")
RRA_EBM_BASE_URL    = os.environ.get("RRA_EBM_BASE_URL",    "http://ebm-mock:8001")
RURA_API_BASE_URL   = os.environ.get("RURA_API_BASE_URL",   "http://rura-mock:8002")
SMS_GATEWAY_URL     = os.environ.get("SMS_GATEWAY_URL",     "http://sms-mock:8003")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOW_ALL_ORIGINS = DEBUG
