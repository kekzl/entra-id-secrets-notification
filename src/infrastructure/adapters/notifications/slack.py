"""Slack notification sender."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ....domain.value_objects import CredentialSource, ExpirationStatus
from .base import BaseNotificationSender

if TYPE_CHECKING:
    from ....domain.entities import Credential, ExpirationReport


@dataclass(frozen=True, slots=True)
class SlackConfig:
    """Slack notification configuration."""

    enabled: bool = False
    webhook_url: str = ""


class SlackNotificationSender(BaseNotificationSender):
    """Send notifications to Slack via incoming webhook."""

    def __init__(self, config: SlackConfig) -> None:
        """Initialize the Slack sender."""
        super().__init__()
        self._config = config

    def is_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return self._config.enabled and bool(self._config.webhook_url)

    async def send(self, report: ExpirationReport) -> bool:
        """Send Slack notification using Block Kit."""
        if not self.is_configured():
            self._logger.warning("Slack sender not configured")
            return False

        try:
            message = self._build_slack_message(report)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

            self._logger.info("Slack notification sent")
            return True

        except Exception:
            self._logger.exception("Failed to send Slack notification")
            return False

    def _build_slack_message(self, report: ExpirationReport) -> dict:
        """Build a Slack message using Block Kit."""
        emoji = report.notification_level.emoji
        color = report.notification_level.color_hex

        blocks: list[dict] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Entra ID Secrets Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{report.get_summary()}*"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Apps Affected:*\n{report.affected_applications_count}"},
                    {"type": "mrkdwn", "text": f"*Total:*\n{report.total_count}"},
                ],
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*🔴 Expired:*\n{report.expired_count}"},
                    {"type": "mrkdwn", "text": f"*🟠 Critical:*\n{report.critical_count}"},
                    {"type": "mrkdwn", "text": f"*🟡 Warning:*\n{report.warning_count}"},
                    {"type": "mrkdwn", "text": f"*🟢 Healthy:*\n{report.healthy_count}"},
                ],
            },
        ]

        # Add App Registration section
        app_creds = report.get_credentials_by_source(CredentialSource.APP_REGISTRATION)
        if app_creds:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*📦 APP REGISTRATIONS*"},
            })
            details = self._build_source_details(report, app_creds)
            if details:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": details},
                })

        # Add Service Principal section
        sp_creds = report.get_credentials_by_source(CredentialSource.SERVICE_PRINCIPAL)
        if sp_creds:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*🔧 SERVICE PRINCIPALS*"},
            })
            details = self._build_source_details(report, sp_creds)
            if details:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": details},
                })

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Entra ID Secrets Notification System"}],
        })

        return {
            "blocks": blocks,
            "attachments": [{"color": color, "blocks": []}],
        }

    def _build_source_details(self, report: ExpirationReport, credentials: list[Credential]) -> str:
        """Build details text for a specific credential source."""
        parts: list[str] = []

        expired = [c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.EXPIRED]
        critical = [c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.CRITICAL]
        warning = [c for c in credentials if c.get_status(report.thresholds) == ExpirationStatus.WARNING]

        if expired:
            parts.append("*🔴 Expired:*")
            for cred in expired[:3]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(
                    f"• `{cred.application_name}` - {cred.credential_type} _{name}_ "
                    f"<{cred.azure_portal_url}|Manage>"
                )

        if critical:
            parts.append("\n*🟠 Critical (≤7 days):*")
            for cred in critical[:3]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(
                    f"• `{cred.application_name}` - _{name}_ ({cred.days_until_expiry}d) "
                    f"<{cred.azure_portal_url}|Manage>"
                )

        if warning:
            parts.append("\n*🟡 Warning (≤30 days):*")
            for cred in warning[:3]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(
                    f"• `{cred.application_name}` - _{name}_ ({cred.days_until_expiry}d) "
                    f"<{cred.azure_portal_url}|Manage>"
                )

        return "\n".join(parts)
