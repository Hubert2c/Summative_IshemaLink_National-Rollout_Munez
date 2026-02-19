"""WebSocket URL routing for tracking."""
from django.urls import re_path
from .consumers import TrackingConsumer

websocket_urlpatterns = [
    re_path(r"^ws/tracking/(?P<tracking_code>[A-Z0-9\-]+)/$", TrackingConsumer.as_asgi()),
]
