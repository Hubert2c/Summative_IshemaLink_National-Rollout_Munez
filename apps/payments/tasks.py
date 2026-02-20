"""
Payment Celery tasks — Phase 6.

TODO: set success rate from settings, not hardcoded (Phase 11)
FIXME: HTTP call to own webhook — fragile, needs circuit breaker
"""

import logging
import random
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def simulate_momo_callback(payment_id: str):
    """
    Phase 6: simulate MoMo async callback.
    90% success rate to mimic real Rwandan mobile money.

    FIXME: calls own webhook via HTTP — this is a dev convenience.
    In production, the real MTN API sends the callback directly.
    TODO: make success_rate configurable via Django settings
    """
    import requests
    from apps.payments.models import Payment

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error("Payment %s not found for callback simulation", payment_id)
        return

    success = random.random() < 0.90  # TODO: move to settings.MOMO_MOCK_SUCCESS_RATE

    payload = {
        "gateway_ref": payment.gateway_ref,
        "status":      "SUCCESS" if success else "FAILED",
        "reason":      "" if success else "Insufficient funds",
    }

    try:
        # FIXME: hardcoded localhost — use settings.OWN_WEBHOOK_URL
        requests.post("http://localhost:8000/api/payments/webhook/", json=payload, timeout=5)
    except Exception as exc:
        logger.warning("Callback simulation failed: %s", exc)
