"""REST polling fallback for live truck coordinates."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.urls import path

from apps.shipments.models import Shipment


@extend_schema(tags=["Tracking"], summary="Polling endpoint for live truck coordinates")
class LiveTrackingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tracking_code):
        try:
            shipment = Shipment.objects.select_related(
                "driver__driver_profile"
            ).get(tracking_code=tracking_code)
        except Shipment.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        if not shipment.driver or not hasattr(shipment.driver, "driver_profile"):
            return Response({"status": shipment.status, "location": None})

        dp = shipment.driver.driver_profile
        return Response({
            "tracking_code": tracking_code,
            "status":        shipment.status,
            "driver":        shipment.driver.full_name,
            "vehicle":       dp.vehicle_plate,
            "location": {
                "lat":       dp.current_lat,
                "lng":       dp.current_lng,
                "last_seen": dp.last_seen,
            } if dp.current_lat else None,
        })


urlpatterns = [
    path("<str:tracking_code>/live/", LiveTrackingView.as_view(), name="tracking-live"),
]
