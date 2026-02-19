"""Payment async tasks."""

import logging
import random
from celery import shared_task

logger = logging.getLogger("ishemalink.payments.tasks")


@shared_task
def simulate_momo_callback(payment_id: str):
    """
    Simulate an MTN/Airtel Money async callback.
    90% success rate to mimic real-world Rwandan mobile money reliability.
    """
    import requests
    from django.conf import settings
    from apps.payments.models import Payment

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error("simulate_momo_callback: payment %s not found", payment_id)
        return

    success = random.random() < 0.90  # 90% success

    payload = {
        "gateway_ref": payment.gateway_ref,
        "status": "SUCCESS" if success else "FAILED",
        "reason": "" if success else "Insufficient funds",
    }

    # Call our own webhook endpoint
    try:
        requests.post(
            "http://web:8000/api/payments/webhook/",
            json=payload,
            timeout=5,
        )
    except Exception as exc:
        logger.warning("simulate_momo_callback HTTP error: %s", exc)
