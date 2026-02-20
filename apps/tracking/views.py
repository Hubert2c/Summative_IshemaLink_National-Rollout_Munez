"""
Tracking REST view — Phase 7 (polling fallback).
WebSocket added in Phase 8.

TODO Phase 8: add WebSocket upgrade header detection
FIXME: no caching — every poll hits the DB
       (add Redis cache with 2s TTL in Phase 11)
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path
from apps.shipments.models import Shipment


class LiveTrackingView(APIView):
    """GET /api/tracking/{tracking_code}/live/ — REST polling fallback."""
    permission_classes = [IsAuthenticated]

    def get(self, request, tracking_code):
        try:
            shipment = Shipment.objects.select_related(
                "driver__driver_profile"
            ).get(tracking_code=tracking_code)
        except Shipment.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        # TODO Phase 11: add Redis cache here — 2 second TTL
        # cache_key = f"tracking:{tracking_code}"
        # cached = cache.get(cache_key)
        # if cached: return Response(cached)

        if not shipment.driver or not hasattr(shipment.driver, "driver_profile"):
            return Response({"status": shipment.status, "location": None})

        dp = shipment.driver.driver_profile
        data = {
            "tracking_code": tracking_code,
            "status":        shipment.status,
            "driver":        shipment.driver.full_name,
            "vehicle":       dp.vehicle_plate,
            "location":      {
                "lat":       dp.current_lat,
                "lng":       dp.current_lng,
                "last_seen": dp.last_seen,
            } if dp.current_lat else None,
        }
        # TODO: cache.set(cache_key, data, 2)
        return Response(data)
