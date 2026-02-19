"""
Notification service.
Supports SMS (via Rwanda SMS gateway) and Email.
In production, swap the HTTP calls with the real provider SDK.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger("ishemalink.notifications")


class NotificationService:
    """Send SMS and Email notifications. Fails silently — never blocks the main flow."""

    def send_sms(self, phone: str, message: str) -> bool:
        """Send SMS via gateway. Returns True on success."""
        try:
            resp = requests.post(
                f"{settings.SMS_GATEWAY_URL}/send",
                json={"phone": phone, "message": message},
                timeout=3,
            )
            if resp.status_code == 200:
                logger.info("SMS sent to %s", phone)
                return True
            logger.warning("SMS gateway returned %s for %s", resp.status_code, phone)
        except requests.RequestException as exc:
            logger.warning("SMS failed for %s: %s", phone, exc)
        return False

    def send_email(self, email: str, subject: str, body: str) -> bool:
        """Send email (stub — wire to SendGrid/AWS SES in production)."""
        logger.info("EMAIL → %s | Subject: %s", email, subject)
        # In production: send via Django email backend or SendGrid API
        return True

    def broadcast_to_drivers(self, message: str) -> int:
        """Send SMS to all active drivers. Returns count sent."""
        from apps.authentication.models import Agent
        drivers = Agent.objects.filter(role="DRIVER", is_active=True)
        sent = 0
        for driver in drivers:
            if self.send_sms(driver.phone, message):
                sent += 1
        logger.info("Broadcast sent to %d drivers", sent)
        return sent
