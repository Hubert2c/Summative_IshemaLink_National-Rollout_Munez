"""
Payment models + Mobile Money gateway adapters.
MomoMock simulates MTN/Airtel Money webhooks for testing.
Production adapters call real MTN MoMo Developer API.
"""

import uuid
import hmac
import hashlib
import logging
from decimal import Decimal

from django.db import models
from django.conf import settings

logger = logging.getLogger("ishemalink.payments")


# ── Model ─────────────────────────────────────────────────────────────────────
class Payment(models.Model):
    class Provider(models.TextChoices):
        MTN_MOMO   = "MTN_MOMO",   "MTN Mobile Money"
        AIRTEL     = "AIRTEL",     "Airtel Money"

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
    gateway_ref = models.CharField(max_length=100, blank=True, db_index=True)
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    ebm_signed  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["gateway_ref"]), models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.shipment.tracking_code} – {self.status} ({self.amount} RWF)"


# ── Gateway Adapter Interface ──────────────────────────────────────────────────
class PaymentGatewayAdapter:
    """Abstract base — all gateways implement this interface."""

    def initiate(self, payment: Payment) -> dict:
        raise NotImplementedError

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError


# ── MTN Momo Mock ─────────────────────────────────────────────────────────────
class MomoMockAdapter(PaymentGatewayAdapter):
    """
    Simulates MTN/Airtel Money push-to-pay flow.
    In production, replace with the real MTN MoMo Developer API client.

    Webhook simulation:
      1. initiate() returns a gateway_ref (e.g., UUID).
      2. A Celery beat task calls self.simulate_callback() after 5 seconds.
      3. The webhook endpoint at /api/payments/webhook/ processes the callback.
    """

    WEBHOOK_SECRET = settings.SECRET_KEY[:32].encode()

    def initiate(self, payment: Payment) -> dict:
        """Send push-to-pay prompt to user's phone (mocked)."""
        import uuid as _uuid
        gateway_ref = str(_uuid.uuid4())
        payment.gateway_ref = gateway_ref
        payment.status      = Payment.Status.PENDING
        payment.save(update_fields=["gateway_ref", "status"])

        logger.info(
            "MOMO MOCK: Push prompt sent to %s for %s RWF. Ref: %s",
            payment.payer_phone, payment.amount, gateway_ref,
        )

        # Schedule simulated callback (90% success rate)
        from apps.payments.tasks import simulate_momo_callback
        simulate_momo_callback.apply_async(
            args=[str(payment.id)],
            countdown=5,  # 5 seconds delay simulates async network round-trip
        )

        return {
            "gateway_ref": gateway_ref,
            "status":      "PENDING",
            "message":     f"Push sent to {payment.payer_phone}. Awaiting confirmation.",
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """HMAC-SHA256 signature verification."""
        expected = hmac.new(self.WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()  # noqa: S324
        return hmac.compare_digest(expected, signature)


# ── Factory ────────────────────────────────────────────────────────────────────
def get_payment_adapter(provider: str) -> PaymentGatewayAdapter:
    adapters = {
        Payment.Provider.MTN_MOMO: MomoMockAdapter,
        Payment.Provider.AIRTEL:  MomoMockAdapter,   # same mock for now
    }
    cls = adapters.get(provider)
    if not cls:
        raise ValueError(f"Unknown payment provider: {provider}")
    return cls()
