import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("authentication", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Zone",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name",         models.CharField(max_length=80, unique=True)),
                ("province",     models.CharField(max_length=50)),
                ("base_rate_kg", models.DecimalField(
                    decimal_places=2, max_digits=8,
                    validators=[django.core.validators.MinValueValidator(0)],
                )),
                ("is_border",    models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Commodity",
            fields=[
                ("id",           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name",         models.CharField(max_length=80, unique=True)),
                ("hs_code",      models.CharField(blank=True, max_length=10)),
                ("is_perishable",models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id",            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tracking_code", models.CharField(db_index=True, max_length=20, unique=True)),
                ("shipment_type", models.CharField(
                    choices=[("DOMESTIC", "Domestic"), ("INTERNATIONAL", "International")],
                    max_length=15,
                )),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT",      "Draft"),
                        ("CONFIRMED",  "Confirmed"),
                        ("PAID",       "Paid"),
                        ("ASSIGNED",   "Driver Assigned"),
                        ("IN_TRANSIT", "In Transit"),
                        ("AT_BORDER",  "At Border / Customs"),
                        ("DELIVERED",  "Delivered"),
                        ("CANCELLED",  "Cancelled"),
                        ("FAILED",     "Failed"),
                    ],
                    default="DRAFT",
                    max_length=12,
                )),
                ("weight_kg",       models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.1)])),
                ("declared_value",  models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("calculated_tariff", models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ("vat_amount",      models.DecimalField(decimal_places=2, max_digits=10, null=True)),
                ("total_amount",    models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ("destination_country",   models.CharField(blank=True, max_length=60)),
                ("customs_manifest_xml",  models.TextField(blank=True)),
                ("ebm_receipt_number",    models.CharField(blank=True, max_length=40)),
                ("ebm_signature",         models.CharField(blank=True, max_length=256)),
                ("notes",                 models.TextField(blank=True)),
                ("created_at",            models.DateTimeField(auto_now_add=True)),
                ("updated_at",            models.DateTimeField(auto_now=True)),
                ("delivered_at",          models.DateTimeField(blank=True, null=True)),
                ("offline_created",       models.BooleanField(default=False)),
                ("sync_id",               models.CharField(blank=True, max_length=64)),
                ("sender",   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="sent_shipments",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("driver",   models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="driven_shipments",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("origin_zone", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="origin_shipments",
                    to="shipments.zone",
                )),
                ("dest_zone",   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="dest_shipments",
                    to="shipments.zone",
                )),
                ("commodity",   models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to="shipments.commodity",
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(fields=["tracking_code"], name="ship_tracking_idx"),
        ),
        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(fields=["status"], name="ship_status_idx"),
        ),
        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(fields=["sender", "status"], name="ship_sender_status_idx"),
        ),
        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(fields=["created_at"], name="ship_created_idx"),
        ),
        migrations.CreateModel(
            name="ShipmentEvent",
            fields=[
                ("id",          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("from_status", models.CharField(max_length=12)),
                ("to_status",   models.CharField(max_length=12)),
                ("note",        models.CharField(blank=True, max_length=255)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("shipment",    models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="shipments.shipment",
                )),
                ("actor",       models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["occurred_at"]},
        ),
    ]
