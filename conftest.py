"""pytest config for dev branch — uses SQLite in-memory."""

import pytest
from django.conf import settings


def pytest_configure(config):
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
                "rest_framework",
                "rest_framework_simplejwt",
                "django_filters",
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
                "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
                "PAGE_SIZE": 50,
            },
            SECRET_KEY="dev-test-secret",
            DEBUG=True,
            USE_TZ=True,
            TIME_ZONE="Africa/Kigali",
            ROOT_URLCONF="ishemalink.urls",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            RRA_EBM_BASE_URL="http://ebm-mock:8001",
            RURA_API_BASE_URL="http://rura-mock:8002",
            SMS_GATEWAY_URL="http://sms-mock:8003",
            MTN_MOMO_BASE_URL="http://momo-mock",
            AIRTEL_MONEY_BASE_URL="http://airtel-mock",
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
            MAINTENANCE_MODE=False,
        )
