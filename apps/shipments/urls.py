from django.urls import path
from .views import ShipmentCreateView, ShipmentListView, ShipmentDetailView, TariffEstimateView

urlpatterns = [
    path("shipments/create/",             ShipmentCreateView.as_view(),  name="shipment-create"),
    path("shipments/",                    ShipmentListView.as_view(),    name="shipment-list"),
    path("shipments/<str:tracking_code>/",ShipmentDetailView.as_view(), name="shipment-detail"),
    path("tariff/estimate/",              TariffEstimateView.as_view(),  name="tariff-estimate"),
]
