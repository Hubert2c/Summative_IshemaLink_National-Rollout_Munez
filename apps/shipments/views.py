"""
Shipment views — Phase 4.

TODO Phase 7: add international shipment create endpoint
TODO Phase 5: integrate payment initiation into create flow
TODO Phase 11: add pagination, filtering by status
FIXME: list view returns ALL shipments — no RBAC filtering yet
"""

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shipment, Zone, Commodity
from .service import BookingService, TariffCalculator
from .serializers import (
    ShipmentCreateSerializer, ShipmentDetailSerializer, TariffEstimateSerializer
)

booking_service = BookingService()


class ShipmentCreateView(generics.CreateAPIView):
    """POST /api/shipments/create/"""
    serializer_class   = ShipmentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        shipment = booking_service.create_shipment(
            sender=self.request.user,
            validated_data=serializer.validated_data,
        )
        self._shipment = shipment

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = ShipmentDetailSerializer(self._shipment)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ShipmentListView(generics.ListAPIView):
    """
    GET /api/shipments/
    FIXME: currently returns all shipments regardless of user role.
    Phase 11 will add proper RBAC — senders see only their own,
    drivers see assigned shipments, admins see all.
    """
    serializer_class   = ShipmentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # TODO Phase 11: filter by role
        # user = self.request.user
        # if user.role == "SENDER": return Shipment.objects.filter(sender=user)
        # if user.role == "DRIVER": return Shipment.objects.filter(driver=user)
        return Shipment.objects.all().select_related(
            "sender", "driver", "origin_zone", "dest_zone", "commodity"
        )


class ShipmentDetailView(generics.RetrieveAPIView):
    """GET /api/shipments/{tracking_code}/"""
    serializer_class   = ShipmentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field       = "tracking_code"

    def get_queryset(self):
        return Shipment.objects.select_related(
            "sender", "driver", "origin_zone", "dest_zone", "commodity"
        )


class TariffEstimateView(APIView):
    """POST /api/tariff/estimate/ — domestic only in Phase 4"""
    permission_classes = [permissions.IsAuthenticated]
    calculator = TariffCalculator()

    def post(self, request):
        ser = TariffEstimateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        class Pseudo:
            origin_zone = d["origin_zone"]
            weight_kg   = d["weight_kg"]
            # TODO Phase 7: shipment_type = d["shipment_type"]
            class commodity:
                is_perishable = d["commodity"].is_perishable

        result = self.calculator.calculate(Pseudo())
        return Response(result)
