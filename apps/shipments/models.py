"""
Shipment models — Phase 4 (domestic only, international coming in Phase 7).

DEVELOPMENT NOTES:
- Phase 3: basic Shipment model, no tariff calculation yet
- Phase 4 (this file): added TariffCalculator for domestic shipments
- Phase 7 (main branch): unified domestic + international into one model

TODO Phase 7: add shipment_type field (DOMESTIC / INTERNATIONAL)
TODO Phase 7: add destination_country, customs_manifest_xml fields
TODO Phase 7: add AT_BORDER status to state machine
TODO Phase 5: add EBM fields (ebm_receipt_number, ebm_signature)
TODO: replace Zone.base_rate_kg placeholder values with real RWF rates
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Zone(models.Model):
    """
    Rwandan logistics zone.
    Phase 3 note: initially used district names directly on Shipment.
    Extracted into Zone model in Phase 3 to support tariff calculation.
    """
    name         = models.CharField(max_length=80, unique=True)
    province     = models.CharField(max_length=50)
    base_rate_kg = models.DecimalField(max_digits=8, decimal_places=2,
                                       validators=[MinValueValidator(0)])
    is_border    = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.province})"


class Commodity(models.Model):
    """Cargo category. Added in Phase 3 after realising we need perishable flag for tariffs."""
    name          = models.CharField(max_length=80, unique=True)
    hs_code       = models.CharField(max_length=10, blank=True)  # TODO: mandatory for Phase 7 international
    is_perishable = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Shipment(models.Model):
    """
    Core shipment — DOMESTIC ONLY in this phase.
    Phase 7 will add international support.
    """

    # Phase 4 state machine — domestic only
    # TODO Phase 7: add AT_BORDER status for international
    class Status(models.TextChoices):
        DRAFT      = "DRAFT",      "Draft"
        CONFIRMED  = "CONFIRMED",  "Confirmed"
        PAID       = "PAID",       "Paid"
        ASSIGNED   = "ASSIGNED",   "Driver Assigned"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED  = "DELIVERED",  "Delivered"
        CANCELLED  = "CANCELLED",  "Cancelled"
        FAILED     = "FAILED",     "Failed"
        # TODO Phase 7: AT_BORDER = "AT_BORDER", "At Border / Customs"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_code = models.CharField(max_length=20, unique=True, db_index=True)
    status        = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    # Hardcoded DOMESTIC for now — Phase 7 will add shipment_type field
    # shipment_type = "DOMESTIC"  # TODO Phase 7: make this a proper field

    sender       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="sent_shipments")
    driver       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="driven_shipments")
    origin_zone  = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="origin_shipments")
    dest_zone    = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="dest_shipments")
    commodity    = models.ForeignKey(Commodity, on_delete=models.PROTECT)

    weight_kg      = models.DecimalField(max_digits=10, decimal_places=2,
                                         validators=[MinValueValidator(0.1)])
    declared_value = models.DecimalField(max_digits=12, decimal_places=2,
                                         validators=[MinValueValidator(0)])

    # Tariff snapshot (calculated on confirmation)
    calculated_tariff = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    vat_amount        = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    total_amount      = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    # TODO Phase 5: EBM fields
    # ebm_receipt_number = models.CharField(max_length=40, blank=True)
    # ebm_signature      = models.CharField(max_length=256, blank=True)

    # TODO Phase 6: offline sync
    # sync_id         = models.CharField(max_length=64, blank=True)
    # offline_created = models.BooleanField(default=False)

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tracking_code} [{self.status}]"


class ShipmentEvent(models.Model):
    """Audit trail. Added in Phase 4 after realising we need traceability for RURA."""
    shipment    = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=12)
    to_status   = models.CharField(max_length=12)
    actor       = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL, null=True)
    note        = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at"]
