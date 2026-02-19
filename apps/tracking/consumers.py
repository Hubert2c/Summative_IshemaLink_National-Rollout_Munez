"""
Real-time tracking.
WebSocket consumer (Django Channels) publishes driver GPS coordinates.
Drivers push location via POST; subscribers receive via WS.
"""

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger("ishemalink.tracking")


class TrackingConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket — subscribe to live tracking for a given tracking_code."""

    async def connect(self):
        self.tracking_code = self.scope["url_route"]["kwargs"]["tracking_code"]
        self.group_name    = f"tracking_{self.tracking_code}"

        # Validate shipment exists
        exists = await self._shipment_exists(self.tracking_code)
        if not exists:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WS connected for %s", self.tracking_code)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        # Drivers push their GPS here
        lat = content.get("lat")
        lng = content.get("lng")
        if lat is not None and lng is not None:
            await self._update_driver_location(self.tracking_code, lat, lng)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "location_update", "lat": lat, "lng": lng, "tracking_code": self.tracking_code},
            )

    async def location_update(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _shipment_exists(self, code):
        from apps.shipments.models import Shipment
        return Shipment.objects.filter(tracking_code=code).exists()

    @database_sync_to_async
    def _update_driver_location(self, code, lat, lng):
        from django.utils import timezone
        from apps.shipments.models import Shipment
        try:
            shipment = Shipment.objects.select_related("driver__driver_profile").get(tracking_code=code)
            if shipment.driver and hasattr(shipment.driver, "driver_profile"):
                dp = shipment.driver.driver_profile
                dp.current_lat = lat
                dp.current_lng = lng
                dp.last_seen   = timezone.now()
                dp.save(update_fields=["current_lat", "current_lng", "last_seen"])
        except Shipment.DoesNotExist:
            pass
