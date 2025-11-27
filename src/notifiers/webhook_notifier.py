"""Generic webhook notification implementation."""

from datetime import datetime, timezone

import requests

from ..config import NotificationConfig
from .base import BaseNotifier, NotificationPayload


class WebhookNotifier(BaseNotifier):
    """Send notifications via generic HTTP webhook."""

    def __init__(self, config: NotificationConfig):
        """Initialize the webhook notifier."""
        super().__init__()
        self.config = config

    def is_configured(self) -> bool:
        """Check if webhook notification is properly configured."""
        return self.config.webhook_enabled and bool(self.config.webhook_url)

    def send(self, payload: NotificationPayload) -> bool:
        """Send a webhook notification with JSON payload."""
        if not self.is_configured():
            self.logger.warning("Webhook notifier is not properly configured")
            return False

        try:
            json_payload = self._build_json_payload(payload)
            response = requests.post(
                self.config.webhook_url,
                json=json_payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            self.logger.info(f"Webhook notification sent to {self.config.webhook_url}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return False

    def _build_json_payload(self, payload: NotificationPayload) -> dict:
        """Build the JSON payload for the webhook."""
        secrets_data = []
        for secret in payload.secrets:
            secrets_data.append(
                {
                    "app_id": secret.app_id,
                    "app_name": secret.app_name,
                    "secret_id": secret.secret_id,
                    "secret_type": secret.secret_type,
                    "display_name": secret.display_name,
                    "expiry_date": secret.expiry_date.isoformat(),
                    "days_until_expiry": secret.days_until_expiry,
                    "is_expired": secret.is_expired,
                }
            )

        return {
            "event_type": "entra_id_secrets_alert",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": payload.level.value,
            "title": payload.title,
            "summary": payload.summary,
            "statistics": {
                "total_apps_affected": payload.total_apps_affected,
                "expired_count": payload.expired_count,
                "critical_count": payload.critical_count,
                "warning_count": payload.warning_count,
                "info_count": payload.info_count,
            },
            "secrets": secrets_data,
        }
