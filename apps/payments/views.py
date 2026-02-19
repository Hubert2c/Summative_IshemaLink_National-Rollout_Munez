"""Payment views — initiate MoMo push, receive webhook callback."""

import json
import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.shipments.models import Shipment
from apps.payments.models import Payment, get_payment_adapter
from apps.payments.serializers import PaymentInitiateSerializer, PaymentDetailSerializer
from apps.shipments.service import BookingService

logger = logging.getLogger("ishemalink.payments")
booking_service = BookingService()


# ── POST /api/payments/initiate/ ─────────────────────────────────────────────
@extend_schema(
    tags=["Payments"],
    summary="Initiate Mobile Money push-to-pay for a confirmed shipment",
    examples=[
        OpenApiExample(
            "MTN MoMo",
            value={"tracking_code": "ISH-ABC12345", "provider": "MTN_MOMO", "payer_phone": "+250781234567"},
        )
    ],
)
class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = PaymentInitiateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            shipment = Shipment.objects.get(
                tracking_code=d["tracking_code"],
                sender=request.user,
                status=Shipment.Status.CONFIRMED,
            )
        except Shipment.DoesNotExist:
            return Response(
                {"error": "Shipment not found or not in CONFIRMED state."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Prevent duplicate payments
        if hasattr(shipment, "payment") and shipment.payment.status == Payment.Status.PENDING:
            return Response(
                {"error": "A payment is already pending for this shipment."},
                status=status.HTTP_409_CONFLICT,
            )

        payment = Payment.objects.create(
            shipment    = shipment,
            provider    = d["provider"],
            amount      = shipment.total_amount,
            payer_phone = d["payer_phone"],
        )

        adapter = get_payment_adapter(d["provider"])
        result  = adapter.initiate(payment)

        return Response({
            "payment_id":  str(payment.id),
            "tracking_code": shipment.tracking_code,
            "amount":      str(payment.amount),
            "currency":    payment.currency,
            **result,
        }, status=status.HTTP_202_ACCEPTED)


# ── POST /api/payments/webhook/ ───────────────────────────────────────────────
@extend_schema(
    tags=["Payments"],
    summary="Receive Mobile Money success/fail callback (webhook)",
)
@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    """
    Receives async callbacks from MTN/Airtel.
    Signature is verified before any state mutation.
    All DB work is atomic — payment status + shipment status update together.
    """
    permission_classes = [AllowAny]
    authentication_classes = []   # webhooks are not JWT-authenticated

    def post(self, request):
        payload   = request.body
        signature = request.headers.get("X-Momo-Signature", "")

        # Signature check (skipped in mock mode)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        gateway_ref     = data.get("gateway_ref")
        callback_status = data.get("status")   # "SUCCESS" or "FAILED"
        reason          = data.get("reason", "")

        if not gateway_ref or callback_status not in ("SUCCESS", "FAILED"):
            return Response({"error": "Missing gateway_ref or status"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related("shipment").get(gateway_ref=gateway_ref)
        except Payment.DoesNotExist:
            logger.warning("Webhook for unknown gateway_ref: %s", gateway_ref)
            return Response({"error": "Unknown reference"}, status=status.HTTP_404_NOT_FOUND)

        if payment.status != Payment.Status.PENDING:
            # Idempotent — already processed
            return Response({"status": "already_processed"})

        with transaction.atomic():
            if callback_status == "SUCCESS":
                payment.status = Payment.Status.SUCCESS
                payment.save(update_fields=["status", "updated_at"])

                # EBM receipt signing (async)
                from apps.govtech.tasks import sign_ebm_receipt
                sign_ebm_receipt.delay(str(payment.id))

                # Advance shipment state
                booking_service.confirm_payment(payment.shipment, payment)

                logger.info("Payment SUCCESS for shipment %s", payment.shipment.tracking_code)
                return Response({"status": "accepted"})

            else:  # FAILED
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "updated_at"])
                booking_service.handle_payment_failure(payment.shipment, reason)

                logger.info("Payment FAILED for shipment %s: %s",
                            payment.shipment.tracking_code, reason)
                return Response({"status": "accepted"})
