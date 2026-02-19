"""Celery tasks for shipment lifecycle."""

import logging
from celery import shared_task

logger = logging.getLogger("ishemalink.tasks")


@shared_task(bind=True, max_retries=5, default_retry_delay=300)
def retry_driver_assignment(self, shipment_id: str):
    """Retry driver assignment when no drivers were available."""
    from apps.shipments.models import Shipment
    from apps.shipments.service import BookingService

    try:
        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.status == Shipment.Status.PAID:
            service = BookingService()
            service.assign_driver(shipment)
            logger.info("Driver assigned on retry for %s", shipment.tracking_code)
    except Shipment.DoesNotExist:
        logger.error("Shipment %s not found for driver retry", shipment_id)
    except Exception as exc:
        logger.warning("Driver assignment retry failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def auto_fail_unpaid_shipments():
    """
    Cron task: mark CONFIRMED shipments older than 30 minutes as FAILED.
    Prevents ghost bookings from blocking inventory.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.shipments.models import Shipment, ShipmentEvent

    cutoff = timezone.now() - timedelta(minutes=30)
    stale = Shipment.objects.filter(
        status=Shipment.Status.CONFIRMED,
        created_at__lt=cutoff,
    )
    for s in stale:
        s.status = Shipment.Status.FAILED
        s.notes  = "Auto-cancelled: payment timeout"
        s.save(update_fields=["status", "notes"])
        ShipmentEvent.objects.create(
            shipment=s, from_status=Shipment.Status.CONFIRMED,
            to_status=Shipment.Status.FAILED,
            note="System auto-cancel: payment timeout",
        )
    logger.info("Auto-failed %d stale shipments", stale.count())
