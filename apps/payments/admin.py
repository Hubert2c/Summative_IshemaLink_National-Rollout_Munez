from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ("shipment", "provider", "amount", "currency", "payer_phone", "status", "ebm_signed", "created_at")
    list_filter   = ("status", "provider", "ebm_signed")
    search_fields = ("payer_phone", "gateway_ref", "shipment__tracking_code")
    readonly_fields = ("id", "created_at", "updated_at")
