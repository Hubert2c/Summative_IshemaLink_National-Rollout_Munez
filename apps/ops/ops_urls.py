from django.urls import path
from .views import MetricsView, MaintenanceToggleView

urlpatterns = [
    path("metrics/",             MetricsView.as_view(),          name="ops-metrics"),
    path("maintenance/toggle/",  MaintenanceToggleView.as_view(), name="ops-maintenance"),
]
