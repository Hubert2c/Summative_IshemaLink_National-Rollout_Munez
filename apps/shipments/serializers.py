"""
Shipment serializers — Phase 4.

TODO Phase 7: add shipment_type, destination_country fields
TODO Phase 5: add sync_id, offline_created fields
TODO: add ShipmentEventSerializer once audit trail is stable
"""

from rest_framework import serializers
from .models import Shipment, Zone, Commodity, ShipmentEvent


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Zone
        fields = ["id", "name", "province", "base_rate_kg"]


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Commodity
        fields = ["id", "name", "hs_code", "is_perishable"]


class ShipmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Shipment
        fields = [
            "origin_zone", "dest_zone", "commodity",
            "weight_kg", "declared_value", "notes",
            # TODO Phase 7: "shipment_type", "destination_country"
            # TODO Phase 5: "sync_id", "offline_created"
        ]

    def validate(self, data):
        if data.get("origin_zone") == data.get("dest_zone"):
            raise serializers.ValidationError("Origin and destination zones must differ.")
        if data.get("weight_kg", 0) <= 0:
            raise serializers.ValidationError("Weight must be positive.")
        return data


class ShipmentDetailSerializer(serializers.ModelSerializer):
    origin_zone = ZoneSerializer(read_only=True)
    dest_zone   = ZoneSerializer(read_only=True)
    commodity   = CommoditySerializer(read_only=True)
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default=None)

    class Meta:
        model  = Shipment
        fields = [
            "id", "tracking_code", "status",
            # TODO Phase 7: "shipment_type"
            "sender_name", "driver_name",
            "origin_zone", "dest_zone", "commodity",
            "weight_kg", "declared_value",
            "calculated_tariff", "vat_amount", "total_amount",
            "notes", "created_at",
        ]


class TariffEstimateSerializer(serializers.Serializer):
    origin_zone = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all())
    commodity   = serializers.PrimaryKeyRelatedField(queryset=Commodity.objects.all())
    weight_kg   = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.1)
    # TODO Phase 7: shipment_type field for international surcharge
