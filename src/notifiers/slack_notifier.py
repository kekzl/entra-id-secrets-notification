"""Slack notification implementation."""

import requests

from ..config import NotificationConfig
from .base import BaseNotifier, NotificationLevel, NotificationPayload


class SlackNotifier(BaseNotifier):
    """Send notifications to Slack via incoming webhook."""

    def __init__(self, config: NotificationConfig):
        """Initialize the Slack notifier."""
        super().__init__()
        self.config = config

    def is_configured(self) -> bool:
        """Check if Slack notification is properly configured."""
        return self.config.slack_enabled and bool(self.config.slack_webhook_url)

    def send(self, payload: NotificationPayload) -> bool:
        """Send a Slack notification using Block Kit."""
        if not self.is_configured():
            self.logger.warning("Slack notifier is not properly configured")
            return False

        try:
            message = self._build_slack_message(payload)
            response = requests.post(
                self.config.slack_webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            self.logger.info("Slack notification sent successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _build_slack_message(self, payload: NotificationPayload) -> dict:
        """Build a Slack message using Block Kit."""
        emoji = self.get_level_emoji(payload.level)
        color = self.get_level_color(payload.level)

        # Build the main blocks
        blocks = [
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
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{payload.summary}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Applications Affected:*\n{payload.total_apps_affected}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Secrets:*\n{len(payload.secrets)}",
                    },
                ],
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*🔴 Expired:*\n{payload.expired_count}"},
                    {"type": "mrkdwn", "text": f"*🟠 Critical:*\n{payload.critical_count}"},
                    {"type": "mrkdwn", "text": f"*🟡 Warning:*\n{payload.warning_count}"},
                    {"type": "mrkdwn", "text": f"*🟢 Info:*\n{payload.info_count}"},
                ],
            },
            {"type": "divider"},
        ]

        # Add details for critical secrets
        expired = [s for s in payload.secrets if s.is_expired]
        critical = [s for s in payload.secrets if not s.is_expired and s.days_until_expiry <= 7]
        warning = [
            s for s in payload.secrets if not s.is_expired and 7 < s.days_until_expiry <= 30
        ]

        details_text = ""

        if expired:
            details_text += "*🔴 Expired:*\n"
            for s in expired[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_text += f"• `{s.app_name}` - {s.secret_type} _{secret_name}_\n"

        if critical:
            details_text += "\n*🟠 Critical (≤7 days):*\n"
            for s in critical[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_text += (
                    f"• `{s.app_name}` - {s.secret_type} _{secret_name}_ "
                    f"({s.days_until_expiry}d)\n"
                )

        if warning:
            details_text += "\n*🟡 Warning (≤30 days):*\n"
            for s in warning[:5]:
                secret_name = s.display_name or s.secret_id[:8]
                details_text += (
                    f"• `{s.app_name}` - {s.secret_type} _{secret_name}_ "
                    f"({s.days_until_expiry}d)\n"
                )

        if details_text:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": details_text.strip()},
                }
            )

        # Add context footer
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Entra ID Secrets Notification System",
                    }
                ],
            }
        )

        message = {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "blocks": [],
                }
            ],
        }

        return message
