"""Microsoft Teams notification sender."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ....domain.value_objects import CredentialSource, ExpirationStatus
from .base import BaseNotificationSender

if TYPE_CHECKING:
    from ....domain.entities import Credential, ExpirationReport


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

        body_items: list[dict] = [
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
                "text": report.get_summary(),
                "wrap": True,
                "size": "Medium",
            },
            {"type": "FactSet", "facts": facts},
        ]

        # Add App Registration section
        app_creds = report.get_credentials_by_source(CredentialSource.APP_REGISTRATION)
        if app_creds:
            body_items.extend(
                self._build_source_section(report, app_creds, "App Registrations", "#0078D4")
            )

        # Add Service Principal section
        sp_creds = report.get_credentials_by_source(CredentialSource.SERVICE_PRINCIPAL)
        if sp_creds:
            body_items.extend(
                self._build_source_section(report, sp_creds, "Service Principals", "#5C2D91")
            )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentVersion": "1.4",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body_items,
                    },
                }
            ],
        }

    def _build_source_section(
        self,
        report: ExpirationReport,
        credentials: list[Credential],
        title: str,
        _color: str,
    ) -> list[dict]:
        """Build Adaptive Card section for a credential source."""
        items: list[dict] = [
            {
                "type": "TextBlock",
                "text": f"**{title}**",
                "wrap": True,
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent",
                "spacing": "Large",
            },
        ]

        # Group by status
        expired = [
            c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.EXPIRED
        ]
        critical = [
            c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.CRITICAL
        ]
        warning = [
            c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.WARNING
        ]

        if expired:
            items.append(
                {
                    "type": "TextBlock",
                    "text": "🔴 **Expired:**",
                    "wrap": True,
                    "weight": "Bolder",
                }
            )
            for cred in expired[:3]:
                name = cred.display_name or str(cred.id)[:8]
                items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {cred.application_name} - {cred.credential_type} '{name}' "
                        f"[Manage]({cred.azure_portal_url})",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        if critical:
            items.append(
                {
                    "type": "TextBlock",
                    "text": "🟠 **Critical (≤7 days):**",
                    "wrap": True,
                    "weight": "Bolder",
                    "spacing": "Medium",
                }
            )
            for cred in critical[:3]:
                name = cred.display_name or str(cred.id)[:8]
                items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {cred.application_name} - '{name}' ({cred.days_until_expiry}d) "
                        f"[Manage]({cred.azure_portal_url})",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        if warning:
            items.append(
                {
                    "type": "TextBlock",
                    "text": "🟡 **Warning (≤30 days):**",
                    "wrap": True,
                    "weight": "Bolder",
                    "spacing": "Medium",
                }
            )
            for cred in warning[:3]:
                name = cred.display_name or str(cred.id)[:8]
                items.append(
                    {
                        "type": "TextBlock",
                        "text": f"• {cred.application_name} - '{name}' ({cred.days_until_expiry}d) "
                        f"[Manage]({cred.azure_portal_url})",
                        "wrap": True,
                        "spacing": "None",
                    }
                )

        return items
