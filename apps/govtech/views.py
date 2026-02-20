"""
GovTech views — Phase 9.

TODO Phase 9 final: EBM signing should be async (Celery task), not blocking
TODO Phase 10: RURA verify should cache results for 24h (license doesn't change daily)
FIXME: CustomsManifest endpoint has no check that EBM receipt exists first
"""

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from apps.govtech.connectors import RRAConnector, RURAConnector, CustomsManifestGenerator
from apps.payments.models import Payment
from apps.shipments.models import Shipment

rura_conn  = RURAConnector()
manifest   = CustomsManifestGenerator()


class EBMSignReceiptView(APIView):
    """POST /api/gov/ebm/sign-receipt/"""
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

        # TODO Phase 9 final: make this async — sign_receipt blocks the thread
        result = RRAConnector().sign_receipt(payment)

        payment.shipment.ebm_receipt_number = result["receipt_number"]
        payment.shipment.ebm_signature      = result["signature"]
        payment.shipment.save(update_fields=["ebm_receipt_number", "ebm_signature"])

        return Response(result)


class RURAVerifyView(APIView):
    """GET /api/gov/rura/verify-license/{license_no}/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, license_no):
        # TODO Phase 10: cache result for 24h in Redis
        valid = rura_conn.verify_license(license_no)
        return Response({"license_number": license_no, "valid": valid})


class CustomsManifestView(APIView):
    """POST /api/gov/customs/generate-manifest/"""
    permission_classes = [IsAuthenticated]

    class Serializer(serializers.Serializer):
        tracking_code = serializers.CharField()

    def post(self, request):
        ser = self.Serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # FIXME: no check that ebm_receipt_number exists before generating manifest
        try:
            shipment = Shipment.objects.select_related("sender", "commodity").get(
                tracking_code=ser.validated_data["tracking_code"],
                shipment_type="INTERNATIONAL",
            )
        except Shipment.DoesNotExist:
            return Response({"error": "International shipment not found."}, status=404)

        xml_content = manifest.generate(shipment)
        shipment.customs_manifest_xml = xml_content
        shipment.save(update_fields=["customs_manifest_xml"])
        return HttpResponse(xml_content, content_type="application/xml")


class AuditLogView(APIView):
    """GET /api/gov/audit/access-log/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("ADMIN", "INSPECTOR"):
            return Response({"error": "Insufficient permissions."}, status=403)

        from apps.shipments.models import ShipmentEvent
        events = ShipmentEvent.objects.select_related("shipment", "actor").order_by("-occurred_at")[:200]
        # TODO Phase 10: paginate this — 200 row limit is a dev shortcut
        data = [
            {
                "shipment":    e.shipment.tracking_code,
                "from_status": e.from_status,
                "to_status":   e.to_status,
                "actor":       e.actor.full_name if e.actor else "System",
                "note":        e.note,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]
        return Response({"count": len(data), "events": data})
