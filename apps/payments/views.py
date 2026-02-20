"""
Payment views — Phase 5/6.

DEVELOPMENT NOTES:
- Phase 5: initiate view added, webhook is a stub
- Phase 6 (this file): webhook implemented but no signature check yet
- Phase 6 final (main): added HMAC verification, full atomic transaction

TODO: add HMAC signature check on webhook (Phase 6 final)
TODO: add duplicate webhook handling (idempotency check on gateway_ref)
FIXME: webhook has no authentication — any POST will be accepted
       (signature check added in main branch)
"""

import json
import logging

from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shipments.models import Shipment
from apps.payments.models import Payment, get_payment_adapter

logger = logging.getLogger(__name__)


class PaymentInitiateView(APIView):
    """POST /api/payments/initiate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tracking_code = request.data.get("tracking_code")
        provider      = request.data.get("provider", "MTN_MOMO")
        payer_phone   = request.data.get("payer_phone")

        if not tracking_code or not payer_phone:
            return Response(
                {"error": "tracking_code and payer_phone required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            shipment = Shipment.objects.get(
                tracking_code=tracking_code,
                sender=request.user,
                status=Shipment.Status.CONFIRMED,
            )
        except Shipment.DoesNotExist:
            return Response({"error": "Shipment not found or not CONFIRMED."}, status=404)

        payment = Payment.objects.create(
            shipment    = shipment,
            provider    = provider,
            amount      = shipment.total_amount or 0,
            payer_phone = payer_phone,
        )

        adapter = get_payment_adapter(provider)
        result  = adapter.initiate(payment)

        return Response({
            "payment_id":   str(payment.id),
            "tracking_code": tracking_code,
            "amount":        str(payment.amount),
            "currency":      "RWF",
            **result,
        }, status=status.HTTP_202_ACCEPTED)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    """
    POST /api/payments/webhook/
    Receives MoMo callback.

    Phase 6: basic implementation — no signature check yet.
    TODO: add X-Momo-Signature HMAC-SHA256 verification (Phase 6 final)
    TODO: wrap in atomic transaction (Phase 6 final)
    FIXME: no check for duplicate callbacks — same gateway_ref processed twice
           will create double status updates
    """
    permission_classes  = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=400)

        gateway_ref     = data.get("gateway_ref")
        callback_status = data.get("status")

        if not gateway_ref or callback_status not in ("SUCCESS", "FAILED"):
            return Response({"error": "gateway_ref and status required"}, status=400)

        try:
            payment = Payment.objects.select_related("shipment").get(
                gateway_ref=gateway_ref
            )
        except Payment.DoesNotExist:
            logger.warning("Unknown gateway_ref in webhook: %s", gateway_ref)
            return Response({"error": "Unknown reference"}, status=404)

        # TODO Phase 6 final: wrap below in transaction.atomic()
        if callback_status == "SUCCESS":
            payment.status = Payment.Status.SUCCESS
            payment.save(update_fields=["status"])

            shipment        = payment.shipment
            shipment.status = Shipment.Status.PAID
            shipment.save(update_fields=["status"])

            # TODO Phase 9: trigger EBM receipt signing (async Celery task)
            # TODO: notify sender via SMS (Phase 5 notification service)

            logger.info("Payment SUCCESS: %s", payment.shipment.tracking_code)

        else:
            payment.status          = Payment.Status.FAILED
            payment.shipment.status = Shipment.Status.FAILED
            payment.save(update_fields=["status"])
            payment.shipment.save(update_fields=["status"])
            # TODO: notify sender of failure via SMS

            logger.info("Payment FAILED: %s", payment.shipment.tracking_code)

        return Response({"status": "accepted"})
