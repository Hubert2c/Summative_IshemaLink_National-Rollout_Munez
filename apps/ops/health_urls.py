"""Ops health URLs."""
from django.urls import path
from .views import DeepHealthView

urlpatterns = [
    path("deep/", DeepHealthView.as_view(), name="health-deep"),
]
