"""
Notification service — Phase 5 (stub).

DEVELOPMENT NOTES:
- Phase 5 (this file): SMS and email just log to console in dev.
  No real HTTP calls to gateway yet.
- Phase 11 (main): wired up to real SMS gateway URL from settings.

TODO Phase 11: replace logger.info with real HTTP POST to SMS gateway
TODO Phase 11: wire email to SendGrid or AWS SES
TODO: broadcast_to_drivers should be a Celery task (not blocking)
"""

import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Dev stub — all notifications are logged, none actually sent."""

    def send_sms(self, phone: str, message: str) -> bool:
        # TODO Phase 11: POST to settings.SMS_GATEWAY_URL
        logger.info("[DEV SMS] To: %s | %s", phone, message)
        return True  # always "succeeds" in dev

    def send_email(self, email: str, subject: str, body: str) -> bool:
        # TODO Phase 11: wire to Django email backend (SendGrid in prod)
        logger.info("[DEV EMAIL] To: %s | Subject: %s", email, subject)
        return True

    def broadcast_to_drivers(self, message: str) -> int:
        """
        Send SMS to all active drivers.
        TODO: run as Celery task — blocking in current form for large driver pools
        """
        from apps.authentication.models import Agent
        drivers = Agent.objects.filter(role="DRIVER", is_active=True)
        sent = 0
        for driver in drivers:
            if self.send_sms(driver.phone, message):
                sent += 1
        logger.info("[DEV BROADCAST] Sent to %d drivers", sent)
        return sent
