from django.urls import path
from .views import SeedView, SecurityHealthView, LoadSimulationView

urlpatterns = [
    path("seed/",              SeedView.as_view(),            name="test-seed"),
    path("load-simulation/",   LoadSimulationView.as_view(),  name="test-load"),
    path("security-health/",   SecurityHealthView.as_view(),  name="test-security"),
]
