"""
Ops views — Phase 11 (development).

DEVELOPMENT NOTES:
- Phase 11 (this file): basic health check and DB seeder.
  Prometheus metrics, maintenance mode added in main (Phase 11 final).

TODO Phase 11 final: add Prometheus-formatted metrics endpoint
TODO Phase 11 final: add maintenance mode toggle
FIXME: DeepHealthView disk check uses os.statvfs — won't work on Windows dev machines
FIXME: SeedView has no upper limit on count — could OOM the server
"""

import os
import random
import string
import logging
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

logger = logging.getLogger(__name__)


class DeepHealthView(APIView):
    """GET /api/health/deep/ — checks DB, cache, disk"""
    permission_classes  = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {}

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"

        try:
            cache.set("hc", "1", 5)
            checks["redis"] = "ok" if cache.get("hc") == "1" else "miss"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        # FIXME: os.statvfs not available on Windows
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            checks["disk_free_gb"] = round(free_gb, 2)
            checks["disk"] = "ok"
        except Exception as exc:
            checks["disk"] = f"error: {exc}"

        checks["maintenance"] = settings.MAINTENANCE_MODE
        overall = "ok" if all(v in ("ok", False) or isinstance(v, float)
                              for v in checks.values()) else "degraded"
        return Response({"status": overall, "checks": checks})


class DashboardSummaryView(APIView):
    """GET /api/admin/dashboard/summary/ — Admin only"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Admin only."}, status=403)

        from apps.shipments.models import Shipment
        from apps.payments.models import Payment
        from apps.authentication.models import Agent

        return Response({
            "active_trucks_in_transit": Shipment.objects.filter(status="IN_TRANSIT").count(),
            "today_revenue_rwf":        str(
                Payment.objects.filter(status="SUCCESS").aggregate(t=Sum("amount"))["t"] or 0
            ),
            "pending_payments":         Payment.objects.filter(status="PENDING").count(),
            "active_agents":            Agent.objects.filter(is_active=True).count(),
            "shipments_by_status":      dict(Shipment.objects.values_list("status").annotate(c=Count("id"))),
        })


class SeedView(APIView):
    """POST /api/test/seed/ — dev only, seeds dummy shipments"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"error": "Seeding only allowed in DEBUG mode."}, status=403)

        from apps.shipments.models import Shipment, Zone, Commodity

        count = int(request.data.get("count", 50))
        # FIXME: no upper cap — add max count check
        if count > 500:
            return Response({"error": "Max 500 per seed call in dev."}, status=400)

        zones       = list(Zone.objects.all())
        commodities = list(Commodity.objects.all())

        if not zones or not commodities:
            return Response({"error": "Run seed_initial_data management command first."}, status=400)

        created = 0
        for _ in range(count):
            oz, dz = random.sample(zones, 2)
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            Shipment.objects.create(
                tracking_code = f"SEED-{suffix}",
                shipment_type = random.choice(["DOMESTIC", "INTERNATIONAL"]),
                status        = random.choice(["DELIVERED", "IN_TRANSIT", "PAID"]),
                sender        = request.user,
                origin_zone   = oz,
                dest_zone     = dz,
                commodity     = random.choice(commodities),
                weight_kg     = Decimal(random.uniform(10, 5000)).quantize(Decimal("0.01")),
                declared_value= Decimal(random.uniform(5000, 500000)).quantize(Decimal("0.01")),
                total_amount  = Decimal(random.uniform(2000, 80000)).quantize(Decimal("0.01")),
            )
            created += 1

        return Response({"seeded": created})


class SecurityHealthView(APIView):
    """GET /api/test/security-health/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "debug_mode":          settings.DEBUG,
            "secret_key_default":  "CHANGE-ME" in settings.SECRET_KEY,
            "allowed_hosts":       settings.ALLOWED_HOSTS,
            "cors_open":           getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False),
        })
