"""
Analytics views — Phase 10 (first pass).

DEVELOPMENT NOTES:
- Phase 10 (this file): raw GROUP BY queries, no optimisation yet.
  Works fine on dev DB with <1000 rows.
- Phase 11 (main): add materialized views, composite indexes,
  move heavy queries to read replica.

TODO Phase 11: create Materialized Views for top_routes and revenue_heatmap
TODO Phase 11: route analytics queries to read replica DB
TODO Phase 11: add caching (Redis, 1-hour TTL) on all analytics endpoints
FIXME: no row limit on some queries — will be slow on 50k+ shipments
FIXME: driver leaderboard uses full_name — not anonymised (privacy concern for BI)
"""

from django.db.models import Count, Sum, F
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.shipments.models import Shipment
from apps.payments.models import Payment


def _require_admin(request):
    if request.user.role not in ("ADMIN", "INSPECTOR"):
        return Response({"error": "Analytics require ADMIN or INSPECTOR role."}, status=403)
    return None


class TopRoutesView(APIView):
    """GET /api/analytics/routes/top/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _require_admin(request)
        if err:
            return err
        # TODO Phase 11: replace with materialized view query
        # FIXME: no LIMIT applied — add [:20] and log warning if > 1000 rows
        routes = (
            Shipment.objects
            .values(origin=F("origin_zone__name"), destination=F("dest_zone__name"))
            .annotate(shipment_count=Count("id"), total_weight_kg=Sum("weight_kg"))
            .order_by("-shipment_count")[:20]
        )
        return Response(list(routes))


class CommodityBreakdownView(APIView):
    """GET /api/analytics/commodities/breakdown/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _require_admin(request)
        if err:
            return err
        breakdown = (
            Shipment.objects
            .values(commodity_name=F("commodity__name"))
            .annotate(count=Count("id"), total_weight_kg=Sum("weight_kg"), total_value=Sum("declared_value"))
            .order_by("-total_weight_kg")
        )
        return Response(list(breakdown))


class RevenueHeatmapView(APIView):
    """GET /api/analytics/revenue/heatmap/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _require_admin(request)
        if err:
            return err
        # TODO Phase 11: add geospatial coordinates to Zone model for real heatmap
        heatmap = (
            Payment.objects
            .filter(status=Payment.Status.SUCCESS)
            .values(zone=F("shipment__origin_zone__name"), province=F("shipment__origin_zone__province"))
            .annotate(total_revenue=Sum("amount"), shipment_count=Count("id"))
            .order_by("-total_revenue")
        )
        return Response(list(heatmap))


class DriverLeaderboardView(APIView):
    """GET /api/analytics/drivers/leaderboard/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _require_admin(request)
        if err:
            return err
        # FIXME: exposes driver full_name — should be anonymised for MINICOM BI reports
        # TODO Phase 11: replace driver_name with driver_id + aggregate stats only
        drivers = (
            Shipment.objects
            .filter(status=Shipment.Status.DELIVERED, driver__isnull=False)
            .values(driver_name=F("driver__full_name"), vehicle=F("driver__driver_profile__vehicle_plate"))
            .annotate(deliveries=Count("id"), total_kg=Sum("weight_kg"))
            .order_by("-deliveries")[:20]
        )
        return Response(list(drivers))


class MonthlySummaryView(APIView):
    """GET /api/analytics/monthly-summary/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _require_admin(request)
        if err:
            return err
        summary = (
            Shipment.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"), total_weight_kg=Sum("weight_kg"), total_revenue=Sum("total_amount"))
            .order_by("-month")[:12]
        )
        return Response(list(summary))
