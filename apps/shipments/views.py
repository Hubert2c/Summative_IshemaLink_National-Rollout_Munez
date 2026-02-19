"""Shipment API views."""

import logging
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend

from .models import Shipment, Zone, Commodity
from .service import BookingService, TariffCalculator
from . import serializers as sz

logger = logging.getLogger("ishemalink.shipments")
booking_service = BookingService()


# ── POST /api/shipments/create/ ───────────────────────────────────────────────
@extend_schema(tags=["Shipments"], summary="Create a shipment (Domestic or International)")
class ShipmentCreateView(generics.CreateAPIView):
    serializer_class = sz.ShipmentCreateSerializer
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
        out = sz.ShipmentDetailSerializer(self._shipment)
        return Response(out.data, status=status.HTTP_201_CREATED)


# ── GET /api/shipments/ ────────────────────────────────────────────────────────
@extend_schema(tags=["Shipments"], summary="List shipments for the authenticated agent")
class ShipmentListView(generics.ListAPIView):
    serializer_class = sz.ShipmentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "shipment_type"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("ADMIN", "INSPECTOR"):
            return Shipment.objects.select_related("sender", "driver", "origin_zone", "dest_zone", "commodity")
        if user.role == "DRIVER":
            return Shipment.objects.filter(driver=user).select_related("sender", "origin_zone", "dest_zone", "commodity")
        return Shipment.objects.filter(sender=user).select_related("origin_zone", "dest_zone", "commodity")


# ── GET /api/shipments/{tracking_code}/ ───────────────────────────────────────
@extend_schema(tags=["Shipments"], summary="Retrieve shipment by tracking code")
class ShipmentDetailView(generics.RetrieveAPIView):
    serializer_class   = sz.ShipmentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "tracking_code"

    def get_queryset(self):
        return Shipment.objects.select_related("sender", "driver", "origin_zone", "dest_zone", "commodity")


# ── GET /api/tariff/estimate/ ─────────────────────────────────────────────────
@extend_schema(tags=["Shipments"], summary="Estimate tariff before creating a shipment")
class TariffEstimateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    calculator = TariffCalculator()

    def post(self, request):
        ser = sz.TariffEstimateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # Build a lightweight pseudo-shipment for calculation
        class Pseudo:
            origin_zone   = d["origin_zone"]
            weight_kg     = d["weight_kg"]
            shipment_type = d["shipment_type"]
            commodity     = d["commodity"]

        result = self.calculator.calculate(Pseudo())
        return Response(result)
