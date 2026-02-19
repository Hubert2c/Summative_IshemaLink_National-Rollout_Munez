"""Shipment serializers."""

from rest_framework import serializers
from .models import Shipment, Zone, Commodity, ShipmentEvent


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Zone
        fields = ["id", "name", "province", "base_rate_kg", "is_border"]


class CommoditySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Commodity
        fields = ["id", "name", "hs_code", "is_perishable"]


class ShipmentEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model  = ShipmentEvent
        fields = ["from_status", "to_status", "actor_name", "note", "occurred_at"]


class ShipmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Shipment
        fields = [
            "shipment_type", "origin_zone", "dest_zone", "commodity",
            "weight_kg", "declared_value", "destination_country",
            "notes", "sync_id", "offline_created",
        ]

    def validate(self, data):
        if data["shipment_type"] == Shipment.Type.INTERNATIONAL and not data.get("destination_country"):
            raise serializers.ValidationError(
                {"destination_country": "Required for international shipments."}
            )
        if data.get("origin_zone") == data.get("dest_zone"):
            raise serializers.ValidationError("Origin and destination zones must differ.")
        return data


class ShipmentDetailSerializer(serializers.ModelSerializer):
    origin_zone  = ZoneSerializer(read_only=True)
    dest_zone    = ZoneSerializer(read_only=True)
    commodity    = CommoditySerializer(read_only=True)
    events       = ShipmentEventSerializer(many=True, read_only=True)
    sender_name  = serializers.CharField(source="sender.full_name", read_only=True)
    driver_name  = serializers.CharField(source="driver.full_name",  read_only=True, default=None)
    driver_phone = serializers.CharField(source="driver.phone",       read_only=True, default=None)

    class Meta:
        model  = Shipment
        fields = [
            "id", "tracking_code", "shipment_type", "status",
            "sender_name", "driver_name", "driver_phone",
            "origin_zone", "dest_zone", "commodity",
            "weight_kg", "declared_value", "destination_country",
            "calculated_tariff", "vat_amount", "total_amount",
            "ebm_receipt_number", "notes", "events",
            "created_at", "delivered_at",
        ]


class TariffEstimateSerializer(serializers.Serializer):
    origin_zone   = serializers.PrimaryKeyRelatedField(queryset=Zone.objects.all())
    commodity     = serializers.PrimaryKeyRelatedField(queryset=Commodity.objects.all())
    shipment_type = serializers.ChoiceField(choices=Shipment.Type.choices)
    weight_kg     = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.1)
