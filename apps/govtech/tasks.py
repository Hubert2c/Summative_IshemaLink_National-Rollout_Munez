"""GovTech async tasks."""

import logging
from celery import shared_task

logger = logging.getLogger("ishemalink.govtech.tasks")


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def sign_ebm_receipt(self, payment_id: str):
    """Sign EBM receipt asynchronously after payment success."""
    from apps.payments.models import Payment
    from apps.govtech.connectors import RRAConnector

    try:
        payment = Payment.objects.select_related("shipment").get(id=payment_id)
        result  = RRAConnector().sign_receipt(payment)

        payment.shipment.ebm_receipt_number = result["receipt_number"]
        payment.shipment.ebm_signature      = result["signature"]
        payment.shipment.save(update_fields=["ebm_receipt_number", "ebm_signature"])
        payment.ebm_signed = True
        payment.save(update_fields=["ebm_signed"])

        logger.info("EBM receipt signed for payment %s: %s", payment_id, result["receipt_number"])
    except Exception as exc:
        logger.error("EBM signing error: %s", exc)
        raise self.retry(exc=exc)
