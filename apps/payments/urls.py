from django.urls import path
from .views import PaymentInitiateView, PaymentWebhookView

urlpatterns = [
    path("initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    path("webhook/",  PaymentWebhookView.as_view(),  name="payment-webhook"),
]
