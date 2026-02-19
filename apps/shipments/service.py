"""
BookingService — the central orchestrator.

Flow:  create_shipment  →  calculate_tariff  →  initiate_payment  →  assign_driver
                                                     ↑
                                             (called by Momo webhook)
"""

import logging
import random
import string
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.shipments.models import Shipment, ShipmentEvent, Zone
from apps.payments.models import Payment
from apps.notifications.service import NotificationService
from apps.govtech.connectors import RURAConnector

logger = logging.getLogger("ishemalink.booking")

VAT_RATE = Decimal("0.18")   # Rwanda standard VAT


def _generate_tracking_code():
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"ISH-{suffix}"


class TariffCalculator:
    """
    Rule-based tariff engine.
    base_rate comes from the Zone model (RWF per kg).
    International shipments add a 15% cross-border surcharge.
    Perishables add a 10% cold-chain levy.
    """

    INTL_SURCHARGE   = Decimal("0.15")
    PERISHABLE_LEVY  = Decimal("0.10")

    def calculate(self, shipment: Shipment) -> dict:
        base = shipment.origin_zone.base_rate_kg * shipment.weight_kg
        surcharge = Decimal("0")

        if shipment.shipment_type == Shipment.Type.INTERNATIONAL:
            surcharge += base * self.INTL_SURCHARGE

        if shipment.commodity.is_perishable:
            surcharge += base * self.PERISHABLE_LEVY

        subtotal = base + surcharge
        vat      = subtotal * VAT_RATE
        total    = subtotal + vat

        return {
            "base_tariff":  round(base, 2),
            "surcharge":    round(surcharge, 2),
            "vat_amount":   round(vat, 2),
            "total_amount": round(total, 2),
        }


class BookingService:
    """
    Unified booking orchestration.
    Dependencies are injected so they can be swapped in tests.
    """

    def __init__(
        self,
        tariff_calculator=None,
        notification_service=None,
        rura_connector=None,
    ):
        self.tariff_calc   = tariff_calculator   or TariffCalculator()
        self.notifier      = notification_service or NotificationService()
        self.rura          = rura_connector       or RURAConnector()

    # ── Step 1: create ────────────────────────────────────────────────────────
    @transaction.atomic
    def create_shipment(self, sender, validated_data: dict) -> Shipment:
        """
        Create a DRAFT shipment and calculate tariff atomically.
        Idempotent: if sync_id already exists, return existing shipment.
        """
        sync_id = validated_data.get("sync_id", "")
        if sync_id:
            existing = Shipment.objects.filter(sync_id=sync_id).first()
            if existing:
                logger.info("Idempotent create — returning existing %s", existing.tracking_code)
                return existing

        tracking_code = _generate_tracking_code()
        while Shipment.objects.filter(tracking_code=tracking_code).exists():
            tracking_code = _generate_tracking_code()

        shipment = Shipment.objects.create(
            tracking_code = tracking_code,
            sender        = sender,
            **{k: v for k, v in validated_data.items() if k != "sync_id"},
        )
        if sync_id:
            shipment.sync_id = sync_id

        # Snapshot tariff immediately
        tariff = self.tariff_calc.calculate(shipment)
        shipment.calculated_tariff = tariff["base_tariff"] + tariff["surcharge"]
        shipment.vat_amount        = tariff["vat_amount"]
        shipment.total_amount      = tariff["total_amount"]
        shipment.status            = Shipment.Status.CONFIRMED
        shipment.save()

        ShipmentEvent.objects.create(
            shipment=shipment, from_status=Shipment.Status.DRAFT,
            to_status=Shipment.Status.CONFIRMED, actor=sender,
            note="Shipment created and tariff calculated",
        )
        logger.info("Shipment %s created for agent %s", tracking_code, sender.phone)
        return shipment

    # ── Step 2: called by payment webhook on success ───────────────────────
    @transaction.atomic
    def confirm_payment(self, shipment: Shipment, payment: "Payment") -> Shipment:
        """
        Mark shipment as PAID and trigger driver assignment.
        Wrapped in a transaction so payment + status update are atomic.
        """
        if shipment.status != Shipment.Status.CONFIRMED:
            raise ValueError(f"Cannot confirm payment for shipment in state {shipment.status}")

        shipment.status = Shipment.Status.PAID
        shipment.save(update_fields=["status", "updated_at"])

        ShipmentEvent.objects.create(
            shipment=shipment, from_status=Shipment.Status.CONFIRMED,
            to_status=Shipment.Status.PAID, actor=None,
            note=f"Payment {payment.gateway_ref} confirmed",
        )

        # Notify sender via SMS
        self.notifier.send_sms(
            phone=shipment.sender.phone,
            message=(
                f"IshemaLink: Payment received for {shipment.tracking_code}. "
                f"Amount: {payment.amount} RWF. Assigning your driver now."
            ),
        )

        # Assign driver (may raise if none available)
        return self.assign_driver(shipment)

    # ── Step 3: assign driver ─────────────────────────────────────────────────
    @transaction.atomic
    def assign_driver(self, shipment: Shipment) -> Shipment:
        """
        Find nearest available RURA-verified driver and lock with SELECT FOR UPDATE.
        Prevents the race condition where two shipments grab the same driver.
        """
        from apps.authentication.models import DriverProfile, Agent

        # Lock available drivers — serializable isolation handles concurrent access
        driver_profile = (
            DriverProfile.objects
            .select_for_update(skip_locked=True)
            .filter(
                is_available=True,
                rura_verified=True,
                agent__is_active=True,
                capacity_kg__gte=shipment.weight_kg,
            )
            .order_by("?")   # TODO: replace with geo-nearest query
            .first()
        )

        if not driver_profile:
            logger.warning("No drivers available for shipment %s", shipment.tracking_code)
            # Retry via Celery in 5 minutes
            from apps.shipments.tasks import retry_driver_assignment
            retry_driver_assignment.apply_async(
                args=[str(shipment.id)], countdown=300
            )
            return shipment

        # Validate RURA license before assigning
        rura_ok = self.rura.verify_license(driver_profile.license_number)
        if not rura_ok:
            logger.warning(
                "Driver %s failed RURA check — skipping",
                driver_profile.license_number
            )
            driver_profile.rura_verified = False
            driver_profile.save(update_fields=["rura_verified"])
            return self.assign_driver(shipment)  # try next

        driver_profile.is_available = False
        driver_profile.save(update_fields=["is_available"])

        shipment.driver = driver_profile.agent
        shipment.status = Shipment.Status.ASSIGNED
        shipment.save(update_fields=["driver", "status", "updated_at"])

        ShipmentEvent.objects.create(
            shipment=shipment, from_status=Shipment.Status.PAID,
            to_status=Shipment.Status.ASSIGNED,
            actor=driver_profile.agent,
            note=f"Driver {driver_profile.agent.full_name} assigned",
        )

        # Notify both parties
        self.notifier.send_sms(
            phone=shipment.sender.phone,
            message=(
                f"IshemaLink: Driver {driver_profile.agent.full_name} "
                f"({driver_profile.vehicle_plate}) is on the way. "
                f"Track: {shipment.tracking_code}"
            ),
        )
        if shipment.shipment_type == Shipment.Type.INTERNATIONAL:
            self.notifier.send_email(
                email=shipment.sender.phone,   # in real system: exporter email
                subject="Customs Documentation Required",
                body=(
                    f"Dear Exporter,\n\n"
                    f"Your shipment {shipment.tracking_code} has been assigned to "
                    f"{driver_profile.agent.full_name}. Please ensure customs documents "
                    f"are ready for border crossing.\n\nIshemaLink Team"
                ),
            )

        logger.info(
            "Driver %s assigned to shipment %s",
            driver_profile.license_number, shipment.tracking_code
        )
        return shipment

    # ── Rollback on payment failure ────────────────────────────────────────────
    @transaction.atomic
    def handle_payment_failure(self, shipment: Shipment, reason: str) -> Shipment:
        """Cancel booking and release any held resources on payment failure."""
        shipment.status = Shipment.Status.FAILED
        shipment.notes  = f"Payment failed: {reason}"
        shipment.save(update_fields=["status", "notes", "updated_at"])

        ShipmentEvent.objects.create(
            shipment=shipment, from_status=Shipment.Status.CONFIRMED,
            to_status=Shipment.Status.FAILED, actor=None,
            note=f"Payment failure: {reason}",
        )

        self.notifier.send_sms(
            phone=shipment.sender.phone,
            message=(
                f"IshemaLink: Payment failed for {shipment.tracking_code}. "
                f"Reason: {reason}. Please retry."
            ),
        )
        return shipment
