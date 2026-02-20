import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("shipments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id",          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider",    models.CharField(
                    choices=[("MTN_MOMO", "MTN Mobile Money"), ("AIRTEL", "Airtel Money")],
                    max_length=10,
                )),
                ("amount",      models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency",    models.CharField(default="RWF", max_length=3)),
                ("payer_phone", models.CharField(max_length=15)),
                ("gateway_ref", models.CharField(blank=True, db_index=True, max_length=100)),
                ("status",      models.CharField(
                    choices=[
                        ("PENDING",  "Pending"),
                        ("SUCCESS",  "Success"),
                        ("FAILED",   "Failed"),
                        ("REFUNDED", "Refunded"),
                    ],
                    default="PENDING",
                    max_length=10,
                )),
                ("ebm_signed",  models.BooleanField(default=False)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
                ("updated_at",  models.DateTimeField(auto_now=True)),
                ("shipment",    models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="payment",
                    to="shipments.shipment",
                )),
            ],
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["gateway_ref"], name="pay_gateway_ref_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["status"], name="pay_status_idx"),
        ),
    ]
