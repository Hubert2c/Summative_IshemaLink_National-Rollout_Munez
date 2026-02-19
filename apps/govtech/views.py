"""GovTech API views — EBM, RURA, Customs Manifest."""

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.utils import extend_schema

from apps.govtech.connectors import RURAConnector, CustomsManifestGenerator
from apps.payments.models import Payment
from apps.shipments.models import Shipment

rura       = RURAConnector()
manifest   = CustomsManifestGenerator()


# ── POST /api/gov/ebm/sign-receipt/ ──────────────────────────────────────────
@extend_schema(tags=["GovTech"], summary="Request EBM tax receipt signature for a payment")
class EBMSignReceiptView(APIView):
    permission_classes = [IsAuthenticated]

    class Serializer(serializers.Serializer):
        payment_id = serializers.UUIDField()

    def post(self, request):
        ser = self.Serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            payment = Payment.objects.select_related("shipment").get(
                id=ser.validated_data["payment_id"],
                status=Payment.Status.SUCCESS,
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found or not successful."}, status=404)

        from apps.govtech.connectors import RRAConnector
        result = RRAConnector().sign_receipt(payment)

        # Persist signature on shipment
        payment.shipment.ebm_receipt_number = result["receipt_number"]
        payment.shipment.ebm_signature      = result["signature"]
        payment.shipment.save(update_fields=["ebm_receipt_number", "ebm_signature"])
        payment.ebm_signed = True
        payment.save(update_fields=["ebm_signed"])

        return Response(result)


# ── GET /api/gov/rura/verify-license/{license_no}/ ───────────────────────────
@extend_schema(tags=["GovTech"], summary="Verify a driver's RURA transport license")
class RURAVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, license_no):
        valid = rura.verify_license(license_no)
        return Response({"license_number": license_no, "valid": valid})


# ── POST /api/gov/customs/generate-manifest/ ─────────────────────────────────
@extend_schema(tags=["GovTech"], summary="Generate EAC-compliant customs XML manifest")
class CustomsManifestView(APIView):
    permission_classes = [IsAuthenticated]

    class Serializer(serializers.Serializer):
        tracking_code = serializers.CharField()

    def post(self, request):
        ser = self.Serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            shipment = Shipment.objects.select_related(
                "sender", "commodity"
            ).get(
                tracking_code=ser.validated_data["tracking_code"],
                shipment_type=Shipment.Type.INTERNATIONAL,
            )
        except Shipment.DoesNotExist:
            return Response({"error": "International shipment not found."}, status=404)

        xml_content = manifest.generate(shipment)
        shipment.customs_manifest_xml = xml_content
        shipment.save(update_fields=["customs_manifest_xml"])

        return HttpResponse(xml_content, content_type="application/xml")


# ── GET /api/gov/audit/access-log/ ────────────────────────────────────────────
@extend_schema(tags=["GovTech"], summary="Government audit trail (Admin/Inspector only)")
class AuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("ADMIN", "INSPECTOR"):
            return Response({"error": "Insufficient permissions."}, status=403)

        from apps.shipments.models import ShipmentEvent
        events = ShipmentEvent.objects.select_related(
            "shipment", "actor"
        ).order_by("-occurred_at")[:500]

        data = [
            {
                "shipment":     e.shipment.tracking_code,
                "from_status":  e.from_status,
                "to_status":    e.to_status,
                "actor":        e.actor.full_name if e.actor else "System",
                "note":         e.note,
                "occurred_at":  e.occurred_at.isoformat(),
            }
            for e in events
        ]
        return Response({"count": len(data), "events": data})
