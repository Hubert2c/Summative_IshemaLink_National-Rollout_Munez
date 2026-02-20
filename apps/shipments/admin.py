from django.contrib import admin
from .models import Shipment, Zone, Commodity, ShipmentEvent


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display  = ("name", "province", "base_rate_kg", "is_border")
    list_filter   = ("province", "is_border")
    search_fields = ("name",)


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    list_display  = ("name", "hs_code", "is_perishable")
    list_filter   = ("is_perishable",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display  = ("tracking_code", "shipment_type", "status", "sender", "driver", "weight_kg", "total_amount", "created_at")
    list_filter   = ("status", "shipment_type", "origin_zone")
    search_fields = ("tracking_code", "sender__phone", "sender__full_name")
    readonly_fields = ("id", "tracking_code", "created_at", "updated_at")
    ordering      = ("-created_at",)


@admin.register(ShipmentEvent)
class ShipmentEventAdmin(admin.ModelAdmin):
    list_display  = ("shipment", "from_status", "to_status", "actor", "occurred_at")
    readonly_fields = ("occurred_at",)
