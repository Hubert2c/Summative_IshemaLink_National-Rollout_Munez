"""
Shipment Celery tasks — Phase 5 (early).

DEVELOPMENT NOTES:
- Celery not wired up until Phase 5 (requires Redis).
- In dev, run tasks synchronously using .apply() not .delay()
- Phase 11 (main): added beat schedule for auto_fail_unpaid_shipments

TODO Phase 11: configure beat schedule in settings
TODO: add exponential backoff to retry_driver_assignment
FIXME: retry countdown is fixed at 300s — make configurable via settings
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def retry_driver_assignment(self, shipment_id: str):
    """
    Retry driver assignment when none were available at booking time.
    TODO Phase 11: add exponential backoff (300s, 600s, 1200s)
    """
    from apps.shipments.models import Shipment
    from apps.shipments.service import BookingService

    try:
        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.status == Shipment.Status.PAID:
            BookingService().assign_driver(shipment)
    except Shipment.DoesNotExist:
        logger.error("Shipment %s not found for retry", shipment_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def auto_fail_unpaid_shipments():
    """
    Cancel shipments that never got paid.
    TODO Phase 11: wire up to Celery beat — run every 15 minutes
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.shipments.models import Shipment, ShipmentEvent

    cutoff = timezone.now() - timedelta(minutes=30)
    stale  = Shipment.objects.filter(status=Shipment.Status.CONFIRMED, created_at__lt=cutoff)
    for s in stale:
        s.status = Shipment.Status.FAILED
        s.notes  = "Auto-cancelled: payment timeout"
        s.save(update_fields=["status", "notes"])
        ShipmentEvent.objects.create(
            shipment=s, from_status="CONFIRMED", to_status="FAILED",
            note="System: payment timeout"
        )
    logger.info("Auto-failed %d stale shipments", stale.count())
