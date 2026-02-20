"""
pytest configuration for IshemaLink.
Sets Django settings and provides shared fixtures.
"""

import django
import pytest
from django.conf import settings


def pytest_configure(config):
    """Configure Django settings before tests run."""
    if not settings.configured:
        settings.configure(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME":   ":memory:",
                }
            },
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "rest_framework",
                "rest_framework_simplejwt",
                "drf_spectacular",
                "django_filters",
                "corsheaders",
                "apps.authentication",
                "apps.shipments",
                "apps.payments",
                "apps.notifications",
                "apps.tracking",
                "apps.govtech",
                "apps.analytics",
                "apps.ops",
            ],
            AUTH_USER_MODEL="authentication.Agent",
            REST_FRAMEWORK={
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
            },
            SPECTACULAR_SETTINGS={
                "TITLE": "IshemaLink API",
                "DESCRIPTION": "National Logistics Platform — Rwanda",
                "VERSION": "2.0.0",
                "SERVE_INCLUDE_SCHEMA": False,
            },
            SECRET_KEY="test-secret-key-not-for-production",
            DEBUG=True,
            USE_TZ=True,
            TIME_ZONE="Africa/Kigali",
            ROOT_URLCONF="ishemalink.urls",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            TEMPLATES=[{
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            }],
            MIDDLEWARE=[
                "django.middleware.security.SecurityMiddleware",
                "corsheaders.middleware.CorsMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
            ],
            CHANNEL_LAYERS={
                "default": {
                    "BACKEND": "channels.layers.InMemoryChannelLayer",
                }
            },
            ASGI_APPLICATION="ishemalink.asgi.application",
            STATIC_URL="/static/",
            STATIC_ROOT="/tmp/staticfiles_test",
            # Dummy external service URLs (mocked in tests)
            RRA_EBM_BASE_URL="http://ebm-mock:8001",
            RURA_API_BASE_URL="http://rura-mock:8002",
            SMS_GATEWAY_URL="http://sms-mock:8003",
            MTN_MOMO_BASE_URL="http://momo-mock",
            AIRTEL_MONEY_BASE_URL="http://airtel-mock",
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
            CELERY_TASK_ALWAYS_EAGER=True,   # Execute tasks synchronously in tests
            CELERY_TASK_EAGER_PROPAGATES=True,
            MAINTENANCE_MODE=False,
            CORS_ALLOW_ALL_ORIGINS=True,
            SIMPLE_JWT={
                "ACCESS_TOKEN_LIFETIME": __import__("datetime").timedelta(hours=8),
                "REFRESH_TOKEN_LIFETIME": __import__("datetime").timedelta(days=7),
                "ALGORITHM": "HS256",
                "AUTH_HEADER_TYPES": ("Bearer",),
            },
        )
