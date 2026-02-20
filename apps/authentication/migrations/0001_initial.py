import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Agent",
            fields=[
                ("password",     models.CharField(max_length=128, verbose_name="password")),
                ("last_login",   models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("id",           models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone",        models.CharField(max_length=15, unique=True)),
                ("national_id",  models.CharField(blank=True, max_length=16, null=True, unique=True)),
                ("full_name",    models.CharField(max_length=120)),
                ("role",         models.CharField(
                    choices=[
                        ("SENDER", "Sender / Farmer"),
                        ("DRIVER", "Driver"),
                        ("EXPORTER", "Exporter"),
                        ("INSPECTOR", "Customs Inspector"),
                        ("ADMIN", "Admin / Control Tower"),
                    ],
                    default="SENDER",
                    max_length=12,
                )),
                ("district",      models.CharField(blank=True, max_length=50)),
                ("is_active",     models.BooleanField(default=True)),
                ("is_staff",      models.BooleanField(default=False)),
                ("created_at",    models.DateTimeField(auto_now_add=True)),
                ("offline_token", models.CharField(blank=True, max_length=64)),
                ("groups",        models.ManyToManyField(blank=True, related_name="agent_set", to="auth.group")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="agent_perm_set", to="auth.permission")),
            ],
            options={"verbose_name": "Agent"},
        ),
        migrations.AddIndex(
            model_name="agent",
            index=models.Index(fields=["phone"], name="auth_agent_phone_idx"),
        ),
        migrations.AddIndex(
            model_name="agent",
            index=models.Index(fields=["role"], name="auth_agent_role_idx"),
        ),
        migrations.CreateModel(
            name="DriverProfile",
            fields=[
                ("id",              models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("license_number",  models.CharField(max_length=30, unique=True)),
                ("vehicle_plate",   models.CharField(max_length=15, unique=True)),
                ("vehicle_type",    models.CharField(max_length=50)),
                ("capacity_kg",     models.PositiveIntegerField()),
                ("rura_verified",   models.BooleanField(default=False)),
                ("rura_checked_at", models.DateTimeField(blank=True, null=True)),
                ("is_available",    models.BooleanField(default=True)),
                ("current_lat",     models.FloatField(blank=True, null=True)),
                ("current_lng",     models.FloatField(blank=True, null=True)),
                ("last_seen",       models.DateTimeField(blank=True, null=True)),
                ("agent",           models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="driver_profile",
                    to="authentication.agent",
                )),
            ],
        ),
    ]
