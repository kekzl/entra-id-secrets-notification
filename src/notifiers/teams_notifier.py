"""Microsoft Teams notification implementation."""

import requests

from ..config import NotificationConfig
from .base import BaseNotifier, NotificationLevel, NotificationPayload


class TeamsNotifier(BaseNotifier):
    """Send notifications to Microsoft Teams via incoming webhook."""

    def __init__(self, config: NotificationConfig):
        """Initialize the Teams notifier."""
        super().__init__()
        self.config = config

    def is_configured(self) -> bool:
        """Check if Teams notification is properly configured."""
        return self.config.teams_enabled and bool(self.config.teams_webhook_url)

    def send(self, payload: NotificationPayload) -> bool:
        """Send a Teams notification using Adaptive Cards."""
        if not self.is_configured():
            self.logger.warning("Teams notifier is not properly configured")
            return False

        try:
            card = self._build_adaptive_card(payload)
            response = requests.post(
                self.config.teams_webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            self.logger.info("Teams notification sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Teams notification: {e}")
            return False

    def _build_adaptive_card(self, payload: NotificationPayload) -> dict:
        """Build an Adaptive Card for Teams."""
        level_color = self.get_level_color(payload.level)
        emoji = self.get_level_emoji(payload.level)

        # Group secrets by status
        expired = [s for s in payload.secrets if s.is_expired]
        critical = [s for s in payload.secrets if not s.is_expired and s.days_until_expiry <= 7]
        warning = [
            s for s in payload.secrets if not s.is_expired and 7 < s.days_until_expiry <= 30
        ]

        facts = [
            {"title": "Applications Affected", "value": str(payload.total_apps_affected)},
            {"title": "Expired", "value": str(payload.expired_count)},
            {"title": "Critical", "value": str(payload.critical_count)},
            {"title": "Warning", "value": str(payload.warning_count)},
            {"title": "Info", "value": str(payload.info_count)},
        ]

        # Build details section
        details_items = []

        if expired:
            details_items.append(
                {
                    "type": "TextBlock",
                    "text": "🔴 **Expired Secrets:**",
                    "wrap": True,
                    "weight": "Bolder",
                }
            )
            for s in expired[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {s.app_name} - {s.secret_type} '{secret_name}'",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        if critical:
            details_items.append(
                {
                    "type": "TextBlock",
                    "text": "🟠 **Critical (≤7 days):**",
                    "wrap": True,
                    "weight": "Bolder",
                    "spacing": "Medium",
                }
            )
            for s in critical[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {s.app_name} - {s.secret_type} '{secret_name}' ({s.days_until_expiry}d)",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        if warning:
            details_items.append(
                {
                    "type": "TextBlock",
                    "text": "🟡 **Warning (≤30 days):**",
                    "wrap": True,
                    "weight": "Bolder",
                    "spacing": "Medium",
                }
            )
            for s in warning[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {s.app_name} - {s.secret_type} '{secret_name}' ({s.days_until_expiry}d)",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentVersion": "1.4",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "Container",
                                "style": "emphasis",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"{emoji} Entra ID Secrets Alert",
                                        "weight": "Bolder",
                                        "size": "Large",
                                        "wrap": True,
                                    }
                                ],
                            },
                            {
                                "type": "TextBlock",
                                "text": payload.summary,
                                "wrap": True,
                                "size": "Medium",
                            },
                            {
                                "type": "FactSet",
                                "facts": facts,
                            },
                            {
                                "type": "Container",
                                "items": details_items,
                            },
                        ],
                    },
                }
            ],
        }

        return card
