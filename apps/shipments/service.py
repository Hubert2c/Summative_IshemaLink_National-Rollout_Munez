"""
BookingService — Phase 4 (domestic only).

DEVELOPMENT NOTES:
- Phase 3: booking was just a model save, no service layer
- Phase 4 (this file): extracted BookingService + TariffCalculator
- Phase 5 (main): added payment integration, driver RURA verification,
  international surcharges, idempotent sync_id handling

TODO Phase 5: integrate PaymentService — shipment should not be PAID
              until MoMo webhook confirms payment
TODO Phase 5: add idempotency via sync_id (for offline mobile sync)
TODO Phase 7: add international 15% surcharge to TariffCalculator
TODO Phase 9: verify driver RURA license before assigning
FIXME: driver selection is random — need geo-nearest algorithm
FIXME: no retry logic if no drivers are available
"""

import logging
import random
import string
from decimal import Decimal
from django.db import transaction
from apps.shipments.models import Shipment, ShipmentEvent

logger = logging.getLogger(__name__)

VAT_RATE = Decimal("0.18")


def _generate_tracking_code():
    chars  = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"ISH-{suffix}"


class TariffCalculator:
    """
    Domestic tariff only — Phase 4.

    Formula: base_rate * weight_kg + VAT (18%)
    International surcharge (15%) added in Phase 7.
    Perishable levy (10%) — also Phase 7.
    """

    # TODO Phase 7: INTL_SURCHARGE  = Decimal("0.15")
    # TODO Phase 7: PERISHABLE_LEVY = Decimal("0.10")

    def calculate(self, shipment) -> dict:
        base     = shipment.origin_zone.base_rate_kg * shipment.weight_kg
        # TODO Phase 7: apply surcharges based on shipment_type and commodity.is_perishable
        vat      = base * VAT_RATE
        total    = base + vat
        return {
            "base_tariff":  round(base, 2),
            "surcharge":    Decimal("0.00"),  # placeholder — Phase 7
            "vat_amount":   round(vat, 2),
            "total_amount": round(total, 2),
        }


class BookingService:
    """
    Booking orchestration — Phase 4.

    Phase 4 flow: create → calculate tariff → auto-confirm → assign driver
    Phase 5 flow (main): create → calculate → await payment → confirm → assign
    """

    def __init__(self):
        self.tariff_calc = TariffCalculator()
        # TODO Phase 5: inject NotificationService
        # TODO Phase 9: inject RURAConnector

    @transaction.atomic
    def create_shipment(self, sender, validated_data: dict) -> Shipment:
        """
        Phase 4: creates shipment and immediately confirms (no payment yet).
        Phase 5 will hold at CONFIRMED until payment webhook arrives.
        """
        tracking_code = _generate_tracking_code()
        while Shipment.objects.filter(tracking_code=tracking_code).exists():
            tracking_code = _generate_tracking_code()

        shipment = Shipment.objects.create(
            tracking_code=tracking_code,
            sender=sender,
            **validated_data,
        )

        # Calculate and snapshot tariff
        tariff = self.tariff_calc.calculate(shipment)
        shipment.calculated_tariff = tariff["base_tariff"]
        shipment.vat_amount        = tariff["vat_amount"]
        shipment.total_amount      = tariff["total_amount"]

        # Phase 4: skip payment, go straight to CONFIRMED
        # TODO Phase 5: stop here at CONFIRMED, wait for payment webhook
        shipment.status = Shipment.Status.CONFIRMED
        shipment.save()

        ShipmentEvent.objects.create(
            shipment=shipment,
            from_status=Shipment.Status.DRAFT,
            to_status=Shipment.Status.CONFIRMED,
            actor=sender,
            note="Shipment created (dev: payment step skipped)",
        )
        logger.info("Shipment %s created for %s", tracking_code, sender.phone)
        return shipment

    @transaction.atomic
    def assign_driver(self, shipment: Shipment) -> Shipment:
        """
        Assign any available driver.
        FIXME: random selection — replace with geo-nearest in production.
        TODO Phase 9: add RURA license check before assigning.
        TODO: handle race condition — two shipments grabbing same driver
              (need SELECT FOR UPDATE in production — Phase 11)
        """
        from apps.authentication.models import Agent

        # TODO Phase 3: DriverProfile not yet created — querying Agent directly
        driver = (
            Agent.objects
            .filter(role="DRIVER", is_active=True)
            # TODO: .filter(driver_profile__is_available=True) after Phase 3
            # TODO: .filter(driver_profile__rura_verified=True) after Phase 9
            .exclude(id=shipment.sender.id)
            .order_by("?")  # FIXME: random — replace with geo-nearest
            .first()
        )

        if not driver:
            logger.warning("No drivers available for %s", shipment.tracking_code)
            # TODO Phase 5: add Celery retry task here
            return shipment

        # TODO Phase 9: check RURA license validity before this line
        shipment.driver = driver
        shipment.status = Shipment.Status.ASSIGNED
        shipment.save(update_fields=["driver", "status", "updated_at"])

        ShipmentEvent.objects.create(
            shipment=shipment,
            from_status=Shipment.Status.CONFIRMED,
            to_status=Shipment.Status.ASSIGNED,
            actor=driver,
            note=f"Driver {driver.full_name} assigned (dev build)",
        )

        # TODO Phase 5: send SMS to sender via NotificationService
        logger.info("Driver %s assigned to %s", driver.phone, shipment.tracking_code)
        return shipment
