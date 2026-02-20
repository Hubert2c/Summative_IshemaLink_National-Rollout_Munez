"""
Tracking — Phase 8 (WebSocket first attempt).

DEVELOPMENT NOTES:
- Phase 7: tracking was REST-only polling (get latest lat/lng from DB)
- Phase 8 (this file): added Django Channels WebSocket consumer.
  First working version — no auth check on WS connect yet.
- Phase 8 final (main): added shipment existence check on connect,
  close with code 4004 if not found.

TODO: authenticate WebSocket connection (JWT in query param or cookie)
TODO: store GPS history, not just latest point (Phase 9)
FIXME: no rate limiting on location pushes — driver could flood channel
FIXME: _update_driver_location silently fails if DriverProfile not created yet
"""

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class TrackingConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for live truck GPS tracking."""

    async def connect(self):
        self.tracking_code = self.scope["url_route"]["kwargs"]["tracking_code"]
        self.group_name    = f"tracking_{self.tracking_code}"

        # TODO Phase 8 final: validate shipment exists, close 4004 if not
        # exists = await self._shipment_exists(self.tracking_code)
        # if not exists:
        #     await self.close(code=4004)
        #     return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("[DEV WS] Connected: %s", self.tracking_code)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("[DEV WS] Disconnected: %s (code=%s)", self.tracking_code, code)

    async def receive_json(self, content):
        """Driver pushes GPS coordinates here."""
        lat = content.get("lat")
        lng = content.get("lng")

        # TODO: validate lat/lng are valid coordinates
        # TODO: rate limit — max 1 update per second per driver

        if lat is not None and lng is not None:
            await self._update_driver_location(self.tracking_code, lat, lng)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type":          "location_update",
                    "lat":           lat,
                    "lng":           lng,
                    "tracking_code": self.tracking_code,
                },
            )

    async def location_update(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _shipment_exists(self, code):
        from apps.shipments.models import Shipment
        return Shipment.objects.filter(tracking_code=code).exists()

    @database_sync_to_async
    def _update_driver_location(self, code, lat, lng):
        """
        Persist latest GPS to DriverProfile.
        FIXME: silently fails if driver has no DriverProfile (Phase 3 not yet done).
        """
        from django.utils import timezone
        from apps.shipments.models import Shipment
        try:
            shipment = Shipment.objects.select_related(
                "driver__driver_profile"
            ).get(tracking_code=code)

            if shipment.driver and hasattr(shipment.driver, "driver_profile"):
                dp = shipment.driver.driver_profile
                dp.current_lat = lat
                dp.current_lng = lng
                dp.last_seen   = timezone.now()
                dp.save(update_fields=["current_lat", "current_lng", "last_seen"])
            else:
                # FIXME: DriverProfile missing — log and skip
                logger.warning("[DEV] No DriverProfile for driver on %s", code)
        except Shipment.DoesNotExist:
            logger.warning("[DEV WS] Shipment %s not found for location update", code)
