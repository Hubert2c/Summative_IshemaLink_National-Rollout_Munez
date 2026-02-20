"""
Payment models — Phase 5 (early MoMo integration).

DEVELOPMENT NOTES:
- Phase 5 (this file): first attempt at MoMo integration.
  The adapter just logs — webhook not yet implemented.
- Phase 6 (main): full webhook endpoint with HMAC signature verification,
  atomic transaction (payment + shipment status update together).

TODO Phase 6: implement webhook endpoint at /api/payments/webhook/
TODO Phase 6: add HMAC-SHA256 signature verification on webhook
TODO Phase 6: wrap payment update + shipment status in atomic transaction
TODO Phase 6: handle FAILED payment — rollback booking
FIXME: MomoMockAdapter.initiate() does not actually schedule callback yet
       (simulate_momo_callback Celery task added in Phase 6)
"""

import uuid
import logging
from decimal import Decimal

from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)


class Payment(models.Model):

    class Provider(models.TextChoices):
        MTN_MOMO = "MTN_MOMO", "MTN Mobile Money"
        AIRTEL   = "AIRTEL",   "Airtel Money"

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending"
        SUCCESS  = "SUCCESS",  "Success"
        FAILED   = "FAILED",   "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment    = models.OneToOneField(
        "shipments.Shipment", on_delete=models.PROTECT, related_name="payment"
    )
    provider    = models.CharField(max_length=10, choices=Provider.choices)
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    currency    = models.CharField(max_length=3, default="RWF")
    payer_phone = models.CharField(max_length=15)
    gateway_ref = models.CharField(max_length=100, blank=True)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    # TODO Phase 8 (GovTech): ebm_signed = models.BooleanField(default=False)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.shipment.tracking_code} — {self.status} ({self.amount} RWF)"


class MomoMockAdapter:
    """
    Phase 5: basic MoMo push simulation.
    Just logs and assigns a fake gateway_ref — no actual callback yet.
    Phase 6 will add: Celery task to simulate callback after 5 seconds.

    TODO Phase 6: schedule simulate_momo_callback.apply_async(countdown=5)
    TODO Phase 6: add verify_webhook_signature() with HMAC-SHA256
    """

    def initiate(self, payment: Payment) -> dict:
        gateway_ref = str(uuid.uuid4())
        payment.gateway_ref = gateway_ref
        payment.status      = Payment.Status.PENDING
        payment.save(update_fields=["gateway_ref", "status"])

        # Phase 5: just log — no real API call yet
        logger.info(
            "MOMO MOCK (Phase 5 — no real callback): push to %s for %s RWF. ref=%s",
            payment.payer_phone, payment.amount, gateway_ref,
        )
        # TODO Phase 6: uncomment when Celery + Redis is wired up
        # from apps.payments.tasks import simulate_momo_callback
        # simulate_momo_callback.apply_async(args=[str(payment.id)], countdown=5)

        return {
            "gateway_ref": gateway_ref,
            "status":      "PENDING",
            "message":     f"[DEV] Push logged for {payment.payer_phone} — no real SMS sent.",
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        # TODO Phase 6: implement HMAC-SHA256 verification
        # For now, accept all — NOT for production
        logger.warning("Signature verification SKIPPED — dev build only")
        return True


def get_payment_adapter(provider: str):
    # TODO Phase 5: add real MTN MoMo API adapter
    # TODO Phase 5: add real Airtel Money adapter
    return MomoMockAdapter()
