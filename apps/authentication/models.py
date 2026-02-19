"""
Authentication models.
Agent is the custom User — covers Sender, Driver, Exporter, Admin roles.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class AgentManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError("Phone number is required.")
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra)


class Agent(AbstractBaseUser, PermissionsMixin):
    """Every human actor in IshemaLink — identified by phone (Rwandan national ID optional)."""

    class Role(models.TextChoices):
        SENDER    = "SENDER",    "Sender / Farmer"
        DRIVER    = "DRIVER",    "Driver"
        EXPORTER  = "EXPORTER",  "Exporter"
        INSPECTOR = "INSPECTOR", "Customs Inspector"
        ADMIN     = "ADMIN",     "Admin / Control Tower"

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone         = models.CharField(max_length=15, unique=True)
    national_id   = models.CharField(max_length=16, blank=True, null=True, unique=True)
    full_name     = models.CharField(max_length=120)
    role          = models.CharField(max_length=12, choices=Role.choices, default=Role.SENDER)
    district      = models.CharField(max_length=50, blank=True)
    is_active     = models.BooleanField(default=True)
    is_staff      = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    # Offline sync token — used by mobile app
    offline_token = models.CharField(max_length=64, blank=True)

    USERNAME_FIELD  = "phone"
    REQUIRED_FIELDS = ["full_name"]

    objects = AgentManager()

    class Meta:
        verbose_name = "Agent"
        indexes = [models.Index(fields=["phone"]), models.Index(fields=["role"])]

    def __str__(self):
        return f"{self.full_name} ({self.role})"


class DriverProfile(models.Model):
    """Extended info for agents with role=DRIVER."""
    agent           = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name="driver_profile")
    license_number  = models.CharField(max_length=30, unique=True)
    vehicle_plate   = models.CharField(max_length=15, unique=True)
    vehicle_type    = models.CharField(max_length=50)
    capacity_kg     = models.PositiveIntegerField()
    rura_verified   = models.BooleanField(default=False)
    rura_checked_at = models.DateTimeField(null=True, blank=True)
    is_available    = models.BooleanField(default=True)
    current_lat     = models.FloatField(null=True, blank=True)
    current_lng     = models.FloatField(null=True, blank=True)
    last_seen       = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.agent.full_name} – {self.vehicle_plate}"
