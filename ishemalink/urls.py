"""
IshemaLink URL configuration — dev branch.

Phase status:
  Phase 2  ✅ Auth (register, login, JWT)
  Phase 4  ✅ Shipments + TariffCalculator
  Phase 5  ✅ Payments (initiate + webhook stub)
  Phase 7  ✅ International shipments
  Phase 8  ✅ WebSocket tracking
  Phase 9  ✅ GovTech (EBM, RURA, Customs)
  Phase 10 ✅ Analytics
  Phase 11 🔄 Ops (health only — metrics/maintenance TODO)
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView

urlpatterns = [
    path("admin/",   admin.site.urls),

    # OpenAPI (useful in dev — browse at /api/docs/)
    path("api/schema/", SpectacularAPIView.as_view(),       name="schema"),
    path("api/docs/",   SpectacularSwaggerUIView.as_view(), name="swagger-ui"),

    # Auth
    path("api/auth/",           include("apps.authentication.urls")),

    # Core logistics
    path("api/",                include("apps.shipments.urls")),
    path("api/payments/",       include("apps.payments.urls")),
    path("api/tracking/",       include("apps.tracking.urls")),

    # Notifications
    path("api/notifications/",  include("apps.notifications.urls")),

    # GovTech
    path("api/gov/",            include("apps.govtech.urls")),

    # Analytics
    path("api/analytics/",      include("apps.analytics.urls")),

    # Ops
    path("api/admin/",          include("apps.ops.urls")),
    path("api/health/",         include("apps.ops.health_urls")),
    path("api/ops/",            include("apps.ops.ops_urls")),   # TODO: metrics + maintenance
    path("api/test/",           include("apps.ops.test_urls")),
]
