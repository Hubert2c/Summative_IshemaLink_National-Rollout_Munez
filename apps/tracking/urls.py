from django.urls import path
from .views import LiveTrackingView

urlpatterns = [
    path("<str:tracking_code>/live/", LiveTrackingView.as_view(), name="tracking-live"),
]
