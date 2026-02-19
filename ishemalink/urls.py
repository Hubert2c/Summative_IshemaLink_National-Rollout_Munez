"""IshemaLink root URL configuration."""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI
    path("api/schema/",  SpectacularAPIView.as_view(),       name="schema"),
    path("api/docs/",    SpectacularSwaggerUIView.as_view(), name="swagger-ui"),

    # Auth
    path("api/auth/",    include("apps.authentication.urls")),

    # Core logistics
    path("api/",         include("apps.shipments.urls")),
    path("api/payments/",include("apps.payments.urls")),
    path("api/tracking/",include("apps.tracking.urls")),

    # Notifications
    path("api/notifications/", include("apps.notifications.urls")),

    # GovTech
    path("api/gov/",     include("apps.govtech.urls")),

    # Analytics / BI
    path("api/analytics/",include("apps.analytics.urls")),

    # Ops / Admin
    path("api/admin/",  include("apps.ops.urls")),
    path("api/health/", include("apps.ops.health_urls")),
    path("api/ops/",    include("apps.ops.ops_urls")),
    path("api/test/",   include("apps.ops.test_urls")),

    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]
