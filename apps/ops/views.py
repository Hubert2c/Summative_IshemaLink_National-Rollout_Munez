"""
Operations views:
  - Deep health check (DB, Redis, disk)
  - Prometheus-formatted metrics
  - Maintenance mode toggle
  - Admin dashboard summary
  - Test seeding and load simulation
"""

import os
import json
import time
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
from drf_spectacular.utils import extend_schema

logger = logging.getLogger("ishemalink.ops")


# ── GET /api/health/deep/ ─────────────────────────────────────────────────────
@extend_schema(tags=["Ops"], summary="Deep health check — DB, Redis, disk")
class DeepHealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {}

        # Database
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"

        # Redis
        try:
            cache.set("healthcheck", "1", 5)
            checks["redis"] = "ok" if cache.get("healthcheck") == "1" else "miss"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        # Disk
        try:
            stat  = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            checks["disk_free_gb"] = round(free_gb, 2)
            checks["disk"] = "ok" if free_gb > 1 else "low"
        except Exception as exc:
            checks["disk"] = f"error: {exc}"

        # Maintenance mode
        checks["maintenance"] = settings.MAINTENANCE_MODE

        overall = "ok" if all(v in ("ok", False) or isinstance(v, float)
                              for v in checks.values()) else "degraded"
        return Response({"status": overall, "checks": checks})


# ── GET /api/ops/metrics/ ────────────────────────────────────────────────────
@extend_schema(tags=["Ops"], summary="Prometheus-formatted operational metrics")
class MetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.shipments.models import Shipment
        from apps.payments.models import Payment

        shipment_counts = dict(
            Shipment.objects.values_list("status").annotate(c=Count("id"))
        )
        total_revenue = Payment.objects.filter(
            status=Payment.Status.SUCCESS
        ).aggregate(t=Sum("amount"))["t"] or 0

        # Prometheus text format
        lines = [
            "# HELP ishemalink_shipments_total Shipments by status",
            "# TYPE ishemalink_shipments_total gauge",
        ]
        for status, count in shipment_counts.items():
            lines.append(f'ishemalink_shipments_total{{status="{status}"}} {count}')
        lines += [
            "",
            "# HELP ishemalink_revenue_rwf Total confirmed revenue in RWF",
            "# TYPE ishemalink_revenue_rwf gauge",
            f"ishemalink_revenue_rwf {total_revenue}",
        ]
        from django.http import HttpResponse
        return HttpResponse("\n".join(lines), content_type="text/plain; version=0.0.4")


# ── POST /api/ops/maintenance/toggle/ ────────────────────────────────────────
@extend_schema(tags=["Ops"], summary="Toggle maintenance mode (Admin only)")
class MaintenanceToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Admin only."}, status=403)
        settings.MAINTENANCE_MODE = not settings.MAINTENANCE_MODE
        logger.info("Maintenance mode set to %s by %s",
                    settings.MAINTENANCE_MODE, request.user.phone)
        return Response({"maintenance": settings.MAINTENANCE_MODE})


# ── GET /api/admin/dashboard/summary/ ────────────────────────────────────────
@extend_schema(tags=["Admin"], summary="Control Tower — live fleet and revenue overview")
class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Admin only."}, status=403)

        from apps.shipments.models import Shipment
        from apps.payments.models import Payment
        from apps.authentication.models import Agent

        active_trucks  = Shipment.objects.filter(status=Shipment.Status.IN_TRANSIT).count()
        today_revenue  = Payment.objects.filter(
            status=Payment.Status.SUCCESS
        ).aggregate(t=Sum("amount"))["t"] or 0
        pending_payments = Payment.objects.filter(status=Payment.Status.PENDING).count()
        total_agents   = Agent.objects.filter(is_active=True).count()
        shipment_summary = dict(
            Shipment.objects.values_list("status").annotate(c=Count("id"))
        )

        return Response({
            "active_trucks_in_transit": active_trucks,
            "today_revenue_rwf":        str(today_revenue),
            "pending_payments":         pending_payments,
            "active_agents":            total_agents,
            "shipments_by_status":      shipment_summary,
        })


# ── POST /api/test/seed/ ─────────────────────────────────────────────────────
@extend_schema(tags=["Test"], summary="Seed DB with dummy shipments for testing")
class SeedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"error": "Seeding only allowed in DEBUG mode."}, status=403)

        from apps.shipments.models import Shipment, Zone, Commodity
        from apps.authentication.models import Agent

        count = int(request.data.get("count", 100))
        zones = list(Zone.objects.all())
        commodities = list(Commodity.objects.all())
        sender = request.user

        if not zones or not commodities:
            return Response({"error": "Seed Zones and Commodities first via admin."}, status=400)

        created = 0
        for _ in range(count):
            oz, dz = random.sample(zones, 2)
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            Shipment.objects.create(
                tracking_code = f"SEED-{suffix}",
                shipment_type = random.choice([Shipment.Type.DOMESTIC, Shipment.Type.INTERNATIONAL]),
                status        = random.choice([
                    Shipment.Status.DELIVERED, Shipment.Status.IN_TRANSIT, Shipment.Status.PAID
                ]),
                sender        = sender,
                origin_zone   = oz,
                dest_zone     = dz,
                commodity     = random.choice(commodities),
                weight_kg     = Decimal(random.uniform(10, 5000)).quantize(Decimal("0.01")),
                declared_value= Decimal(random.uniform(5000, 500000)).quantize(Decimal("0.01")),
                destination_country = random.choice(["UG", "KE", "TZ", ""]),
                total_amount  = Decimal(random.uniform(2000, 80000)).quantize(Decimal("0.01")),
                offline_created = random.random() < 0.1,
            )
            created += 1

        return Response({"seeded": created})



# ── GET /api/test/load-simulation/ ───────────────────────────────────────────
@extend_schema(tags=["Test"], summary="Trigger internal stress test simulation")
class LoadSimulationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Triggers an internal stress test by simulating concurrent tariff calculations.
        Returns timing results for performance profiling.
        """
        if request.user.role != "ADMIN":
            return Response({"error": "Admin only."}, status=403)

        from apps.shipments.models import Zone, Commodity, Shipment
        from apps.shipments.service import TariffCalculator
        import time

        zones       = list(Zone.objects.all()[:2])
        commodities = list(Commodity.objects.all()[:2])
        if not zones or not commodities:
            return Response({"error": "Seed Zones and Commodities first."}, status=400)

        calc   = TariffCalculator()
        count  = int(request.GET.get("n", 100))
        start  = time.monotonic()
        errors = 0

        for i in range(count):
            try:
                class Pseudo:
                    origin_zone   = zones[i % len(zones)]
                    weight_kg     = Decimal(str(10 + i % 5000))
                    shipment_type = "DOMESTIC" if i % 2 == 0 else "INTERNATIONAL"
                    commodity     = commodities[i % len(commodities)]
                calc.calculate(Pseudo())
            except Exception:
                errors += 1

        elapsed_ms = (time.monotonic() - start) * 1000
        return Response({
            "iterations":        count,
            "errors":            errors,
            "elapsed_ms":        round(elapsed_ms, 2),
            "avg_ms_per_calc":   round(elapsed_ms / count, 3),
            "status":            "ok" if errors == 0 else "degraded",
        })
@extend_schema(tags=["Test"], summary="Security health report")
class SecurityHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "debug_mode":         settings.DEBUG,
            "secret_key_default": settings.SECRET_KEY == "CHANGE-ME-IN-PRODUCTION",
            "allowed_hosts":      settings.ALLOWED_HOSTS,
            "cors_open":          getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False),
            "maintenance_mode":   settings.MAINTENANCE_MODE,
        })
