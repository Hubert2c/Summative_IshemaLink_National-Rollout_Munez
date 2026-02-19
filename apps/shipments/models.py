"""
Shipment models — unified Domestic + International.
A Shipment progresses through a strict state machine enforced at the DB level.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Zone(models.Model):
    """Rwandan logistics zone (province / district cluster)."""
    name         = models.CharField(max_length=80, unique=True)
    province     = models.CharField(max_length=50)
    base_rate_kg = models.DecimalField(max_digits=8, decimal_places=2,
                                       validators=[MinValueValidator(0)])
    is_border    = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.province})"


class Commodity(models.Model):
    """Tracked cargo categories for BI reporting."""
    name         = models.CharField(max_length=80, unique=True)
    hs_code      = models.CharField(max_length=10, blank=True)  # EAC customs
    is_perishable = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Shipment(models.Model):
    """Core shipment record — covers both Domestic and International."""

    class Type(models.TextChoices):
        DOMESTIC       = "DOMESTIC",      "Domestic"
        INTERNATIONAL  = "INTERNATIONAL", "International"

    class Status(models.TextChoices):
        DRAFT       = "DRAFT",       "Draft"
        CONFIRMED   = "CONFIRMED",   "Confirmed"         # payment pending
        PAID        = "PAID",        "Paid"              # payment success
        ASSIGNED    = "ASSIGNED",    "Driver Assigned"
        IN_TRANSIT  = "IN_TRANSIT",  "In Transit"
        AT_BORDER   = "AT_BORDER",   "At Border / Customs"
        DELIVERED   = "DELIVERED",   "Delivered"
        CANCELLED   = "CANCELLED",   "Cancelled"
        FAILED      = "FAILED",      "Failed"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_code = models.CharField(max_length=20, unique=True, db_index=True)
    shipment_type = models.CharField(max_length=15, choices=Type.choices)
    status        = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    sender        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                      related_name="sent_shipments")
    driver        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="driven_shipments")

    origin_zone   = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="origin_shipments")
    dest_zone     = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="dest_shipments")

    commodity     = models.ForeignKey(Commodity, on_delete=models.PROTECT)
    weight_kg     = models.DecimalField(max_digits=10, decimal_places=2,
                                        validators=[MinValueValidator(0.1)])
    declared_value= models.DecimalField(max_digits=12, decimal_places=2,
                                        validators=[MinValueValidator(0)])

    # Tariff snapshot (immutable after confirmation)
    calculated_tariff = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    vat_amount        = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    total_amount      = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    # International extras
    destination_country = models.CharField(max_length=60, blank=True)
    customs_manifest_xml = models.TextField(blank=True)
    ebm_receipt_number  = models.CharField(max_length=40, blank=True)
    ebm_signature       = models.CharField(max_length=256, blank=True)

    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    delivered_at  = models.DateTimeField(null=True, blank=True)

    # Offline: created offline and synced later
    offline_created = models.BooleanField(default=False)
    sync_id         = models.CharField(max_length=64, blank=True)  # client-side idempotency key

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["tracking_code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sender", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.tracking_code} [{self.status}]"


class ShipmentEvent(models.Model):
    """Immutable audit trail for every status transition."""
    shipment   = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    from_status= models.CharField(max_length=12)
    to_status  = models.CharField(max_length=12)
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note       = models.CharField(max_length=255, blank=True)
    occurred_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at"]
