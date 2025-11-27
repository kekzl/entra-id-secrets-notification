"""Slack notification sender."""

from dataclasses import dataclass

import httpx

from ....domain.entities import ExpirationReport
from .base import BaseNotificationSender


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
            {"type": "divider"},
        ]

        # Build details section
        details = self._build_details_text(report)
        if details:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": details},
            })

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Entra ID Secrets Notification System"}],
        })

        return {
            "blocks": blocks,
            "attachments": [{"color": color, "blocks": []}],
        }

    def _build_details_text(self, report: ExpirationReport) -> str:
        """Build details text for Slack message."""
        parts: list[str] = []

        if report.expired:
            parts.append("*🔴 Expired:*")
            for cred in report.expired[:5]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(f"• `{cred.application_name}` - {cred.credential_type} _{name}_")

        if report.critical:
            parts.append("\n*🟠 Critical (≤7 days):*")
            for cred in report.critical[:5]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(f"• `{cred.application_name}` - _{name}_ ({cred.days_until_expiry}d)")

        if report.warning:
            parts.append("\n*🟡 Warning (≤30 days):*")
            for cred in report.warning[:5]:
                name = cred.display_name or str(cred.id)[:8]
                parts.append(f"• `{cred.application_name}` - _{name}_ ({cred.days_until_expiry}d)")

        return "\n".join(parts)
