from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Agent, DriverProfile


@admin.register(Agent)
class AgentAdmin(BaseUserAdmin):
    list_display  = ("phone", "full_name", "role", "district", "is_active", "created_at")
    list_filter   = ("role", "is_active", "district")
    search_fields = ("phone", "full_name", "national_id")
    ordering      = ("-created_at",)
    fieldsets = (
        (None,          {"fields": ("phone", "password")}),
        ("Personal",    {"fields": ("full_name", "national_id", "district")}),
        ("Role",        {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "full_name", "role", "password1", "password2")}),
    )


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display  = ("agent", "license_number", "vehicle_plate", "capacity_kg", "rura_verified", "is_available")
    list_filter   = ("rura_verified", "is_available")
    search_fields = ("license_number", "vehicle_plate", "agent__full_name")
