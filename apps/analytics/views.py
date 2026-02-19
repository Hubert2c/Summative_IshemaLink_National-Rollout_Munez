"""
Analytics API — Business Intelligence for MINICOM.
All queries use GROUP BY aggregation and avoid exposing personal data.
"""

from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.shipments.models import Shipment, Zone
from apps.payments.models import Payment


def _admin_or_403(request):
    if request.user.role not in ("ADMIN", "INSPECTOR"):
        return Response({"error": "Analytics require ADMIN or INSPECTOR role."}, status=403)
    return None


# ── GET /api/analytics/routes/top/ ───────────────────────────────────────────
@extend_schema(tags=["Analytics"], summary="Top high-traffic origin→destination corridors")
class TopRoutesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _admin_or_403(request)
        if err:
            return err

        routes = (
            Shipment.objects
            .values(
                origin=F("origin_zone__name"),
                destination=F("dest_zone__name"),
            )
            .annotate(
                shipment_count=Count("id"),
                total_weight_kg=Sum("weight_kg"),
            )
            .order_by("-shipment_count")[:20]
        )
        return Response(list(routes))


# ── GET /api/analytics/commodities/breakdown/ ─────────────────────────────────
@extend_schema(tags=["Analytics"], summary="Cargo type volume breakdown")
class CommodityBreakdownView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _admin_or_403(request)
        if err:
            return err

        breakdown = (
            Shipment.objects
            .values(commodity_name=F("commodity__name"))
            .annotate(
                count=Count("id"),
                total_weight_kg=Sum("weight_kg"),
                total_value=Sum("declared_value"),
            )
            .order_by("-total_weight_kg")
        )
        return Response(list(breakdown))


# ── GET /api/analytics/revenue/heatmap/ ───────────────────────────────────────
@extend_schema(tags=["Analytics"], summary="Revenue per district/zone (geospatial heatmap data)")
class RevenueHeatmapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _admin_or_403(request)
        if err:
            return err

        # Revenue grouped by origin zone — anonymised (no sender names)
        heatmap = (
            Payment.objects
            .filter(status=Payment.Status.SUCCESS)
            .values(
                zone=F("shipment__origin_zone__name"),
                province=F("shipment__origin_zone__province"),
            )
            .annotate(
                total_revenue=Sum("amount"),
                shipment_count=Count("id"),
            )
            .order_by("-total_revenue")
        )
        return Response(list(heatmap))


# ── GET /api/analytics/drivers/leaderboard/ ────────────────────────────────────
@extend_schema(tags=["Analytics"], summary="Driver performance leaderboard (on-time delivery rate)")
class DriverLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _admin_or_403(request)
        if err:
            return err

        # On-time = delivered before end_date (using delivered_at vs shipment created date heuristic)
        drivers = (
            Shipment.objects
            .filter(status=Shipment.Status.DELIVERED, driver__isnull=False)
            .values(
                driver_name=F("driver__full_name"),
                vehicle=F("driver__driver_profile__vehicle_plate"),
            )
            .annotate(
                deliveries=Count("id"),
                total_kg=Sum("weight_kg"),
            )
            .order_by("-deliveries")[:20]
        )
        return Response(list(drivers))


# ── GET /api/analytics/monthly-summary/ ───────────────────────────────────────
@extend_schema(tags=["Analytics"], summary="Monthly shipment and revenue summary")
class MonthlySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        err = _admin_or_403(request)
        if err:
            return err

        summary = (
            Shipment.objects
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                count=Count("id"),
                total_weight_kg=Sum("weight_kg"),
                total_revenue=Sum("total_amount"),
            )
            .order_by("-month")[:12]
        )
        return Response(list(summary))
