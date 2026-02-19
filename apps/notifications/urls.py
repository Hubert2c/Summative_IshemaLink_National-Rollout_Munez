from django.urls import path
from .views import BroadcastView

urlpatterns = [
    path("broadcast/", BroadcastView.as_view(), name="notifications-broadcast"),
]
