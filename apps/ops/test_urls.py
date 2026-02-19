from django.urls import path
from .views import SeedView, SecurityHealthView

urlpatterns = [
    path("seed/",            SeedView.as_view(),          name="test-seed"),
    path("security-health/", SecurityHealthView.as_view(), name="test-security"),
]
