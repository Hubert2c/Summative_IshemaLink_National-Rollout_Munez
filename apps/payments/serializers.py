"""Payment serializers."""
from rest_framework import serializers
from .models import Payment


class PaymentInitiateSerializer(serializers.Serializer):
    tracking_code = serializers.CharField()
    provider      = serializers.ChoiceField(choices=Payment.Provider.choices)
    payer_phone   = serializers.CharField(max_length=15)


class PaymentDetailSerializer(serializers.ModelSerializer):
    tracking_code = serializers.CharField(source="shipment.tracking_code", read_only=True)

    class Meta:
        model  = Payment
        fields = ["id", "tracking_code", "provider", "amount", "currency",
                  "payer_phone", "gateway_ref", "status", "ebm_signed",
                  "created_at", "updated_at"]
