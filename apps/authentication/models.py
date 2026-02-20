"""
Authentication models — Phase 2 (early development).

DEVELOPMENT NOTES:
- Phase 1: started with Django's default User model (AbstractUser)
- Phase 2 (this file): switched to phone-based auth after realising
  email is not the primary identifier for Rwandan farmers.
- Phase 3 (main branch): added DriverProfile, offline_token, NID validation

TODO: add DriverProfile model (Phase 3)
TODO: validate national_id format (16 digits) — Phase 3
TODO: add offline_token for mobile sync — Phase 3
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
    """
    Custom user model using phone as the primary identifier.

    Phase 2 note: we originally used email (Phase 1) but switched
    to phone because MTN Mobile Money uses phone as the account ID.
    This was a key early design decision.
    """

    class Role(models.TextChoices):
        SENDER   = "SENDER",   "Sender / Farmer"
        DRIVER   = "DRIVER",   "Driver"
        EXPORTER = "EXPORTER", "Exporter"
        ADMIN    = "ADMIN",    "Admin"
        # TODO: add INSPECTOR role for customs — Phase 4

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone       = models.CharField(max_length=15, unique=True)
    national_id = models.CharField(max_length=16, blank=True, null=True)  # TODO: unique=True after data cleanup
    full_name   = models.CharField(max_length=120)
    role        = models.CharField(max_length=12, choices=Role.choices, default=Role.SENDER)
    district    = models.CharField(max_length=50, blank=True)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    # TODO Phase 3: offline_token = models.CharField(max_length=64, blank=True)

    USERNAME_FIELD  = "phone"
    REQUIRED_FIELDS = ["full_name"]

    objects = AgentManager()

    class Meta:
        verbose_name = "Agent"

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


# TODO Phase 3: Add DriverProfile model here
# class DriverProfile(models.Model):
#     agent = models.OneToOneField(Agent, ...)
#     license_number = models.CharField(...)
#     rura_verified = models.BooleanField(default=False)
#     ...
