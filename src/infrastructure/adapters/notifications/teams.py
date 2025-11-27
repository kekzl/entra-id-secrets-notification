"""Microsoft Teams notification sender."""

from dataclasses import dataclass

import httpx

from ....domain.entities import ExpirationReport
from .base import BaseNotificationSender


@dataclass(frozen=True, slots=True)
class TeamsConfig:
    """Teams notification configuration."""

    enabled: bool = False
    webhook_url: str = ""


class TeamsNotificationSender(BaseNotificationSender):
    """Send notifications to Microsoft Teams via incoming webhook."""

    def __init__(self, config: TeamsConfig) -> None:
        """Initialize the Teams sender."""
        super().__init__()
        self._config = config

    def is_configured(self) -> bool:
        """Check if Teams is properly configured."""
        return self._config.enabled and bool(self._config.webhook_url)

    async def send(self, report: ExpirationReport) -> bool:
        """Send Teams notification using Adaptive Cards."""
        if not self.is_configured():
            self._logger.warning("Teams sender not configured")
            return False

        try:
            card = self._build_adaptive_card(report)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

            self._logger.info("Teams notification sent")
            return True

        except Exception:
            self._logger.exception("Failed to send Teams notification")
            return False

    def _build_adaptive_card(self, report: ExpirationReport) -> dict:
        """Build an Adaptive Card for Teams."""
        emoji = report.notification_level.emoji

        facts = [
            {"title": "Applications Affected", "value": str(report.affected_applications_count)},
            {"title": "Expired", "value": str(report.expired_count)},
            {"title": "Critical", "value": str(report.critical_count)},
            {"title": "Warning", "value": str(report.warning_count)},
        ]

        details_items: list[dict] = []

        # Add expired credentials
        if report.expired:
            details_items.append({
                "type": "TextBlock",
                "text": "🔴 **Expired:**",
                "wrap": True,
                "weight": "Bolder",
            })
            for cred in report.expired[:5]:
                name = cred.display_name or str(cred.id)[:8]
                details_items.append({
                    "type": "TextBlock",
                    "text": f"• {cred.application_name} - {cred.credential_type} '{name}'",
                    "wrap": True,
                    "spacing": "None",
                })

        # Add critical credentials
        if report.critical:
            details_items.append({
                "type": "TextBlock",
                "text": "🟠 **Critical (≤7 days):**",
                "wrap": True,
                "weight": "Bolder",
                "spacing": "Medium",
            })
            for cred in report.critical[:5]:
                name = cred.display_name or str(cred.id)[:8]
                details_items.append({
                    "type": "TextBlock",
                    "text": f"• {cred.application_name} - '{name}' ({cred.days_until_expiry}d)",
                    "wrap": True,
                    "spacing": "None",
                })

        # Add warning credentials
        if report.warning:
            details_items.append({
                "type": "TextBlock",
                "text": "🟡 **Warning (≤30 days):**",
                "wrap": True,
                "weight": "Bolder",
                "spacing": "Medium",
            })
            for cred in report.warning[:5]:
                name = cred.display_name or str(cred.id)[:8]
                details_items.append({
                    "type": "TextBlock",
                    "text": f"• {cred.application_name} - '{name}' ({cred.days_until_expiry}d)",
                    "wrap": True,
                    "spacing": "None",
                })

        return {
            "type": "message",
            "attachments": [{
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
                            "items": [{
                                "type": "TextBlock",
                                "text": f"{emoji} Entra ID Secrets Alert",
                                "weight": "Bolder",
                                "size": "Large",
                                "wrap": True,
                            }],
                        },
                        {
                            "type": "TextBlock",
                            "text": report.get_summary(),
                            "wrap": True,
                            "size": "Medium",
                        },
                        {"type": "FactSet", "facts": facts},
                        {"type": "Container", "items": details_items},
                    ],
                },
            }],
        }
