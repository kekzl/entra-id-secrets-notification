"""Email notification sender using Microsoft Graph API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import msal

from ....domain.entities import ExpirationReport
from ....domain.value_objects import NotificationLevel
from .base import BaseNotificationSender


@dataclass(frozen=True, slots=True)
class GraphEmailConfig:
    """Microsoft Graph email notification configuration."""

    enabled: bool = False
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    from_address: str = ""  # Sender mailbox (app needs Mail.Send permission)
    to_addresses: str = ""  # Comma-separated recipients
    save_to_sent_items: bool = False


class GraphEmailNotificationSender(BaseNotificationSender):
    """Send notifications via Microsoft Graph API email."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTHORITY_BASE = "https://login.microsoftonline.com"
    SCOPE = ["https://graph.microsoft.com/.default"]

    def __init__(self, config: GraphEmailConfig) -> None:
        """Initialize the Graph email sender."""
        super().__init__()
        self._config = config
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self._msal_app: msal.ConfidentialClientApplication | None = None

    def is_configured(self) -> bool:
        """Check if Graph email is properly configured."""
        return (
            self._config.enabled
            and bool(self._config.tenant_id)
            and bool(self._config.client_id)
            and bool(self._config.client_secret)
            and bool(self._config.from_address)
            and bool(self._config.to_addresses)
        )

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL application instance."""
        if self._msal_app is None:
            authority = f"{self.AUTHORITY_BASE}/{self._config.tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self._config.client_id,
                client_credential=self._config.client_secret,
                authority=authority,
            )
        return self._msal_app

    async def _acquire_token(self) -> str:
        """Acquire access token using client credentials flow."""
        if self._access_token and self._token_expiry:
            if datetime.now(UTC) < self._token_expiry:
                return self._access_token

        app = self._get_msal_app()
        result = app.acquire_token_for_client(scopes=self.SCOPE)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            msg = f"Failed to acquire access token: {error}"
            raise RuntimeError(msg)

        self._access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        self._token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

        return self._access_token

    async def send(self, report: ExpirationReport) -> bool:
        """Send email notification via Graph API."""
        if not self.is_configured():
            self._logger.warning("Graph email sender not configured")
            return False

        try:
            token = await self._acquire_token()
            message = self._build_message(report)

            url = f"{self.GRAPH_BASE_URL}/users/{self._config.from_address}/sendMail"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=message)
                response.raise_for_status()

            self._logger.info("Graph email sent to %s", self._config.to_addresses)
            return True

        except Exception:
            self._logger.exception("Failed to send Graph email")
            return False

    def _build_message(self, report: ExpirationReport) -> dict[str, Any]:
        """Build the Graph API email message payload."""
        recipients = [
            {"emailAddress": {"address": addr.strip()}}
            for addr in self._config.to_addresses.split(",")
        ]

        return {
            "message": {
                "subject": self._format_subject(report),
                "body": {
                    "contentType": "HTML",
                    "content": self._format_html_body(report),
                },
                "toRecipients": recipients,
            },
            "saveToSentItems": self._config.save_to_sent_items,
        }

    def _format_subject(self, report: ExpirationReport) -> str:
        """Format email subject line."""
        prefix = {
            NotificationLevel.CRITICAL: "[CRITICAL]",
            NotificationLevel.WARNING: "[WARNING]",
            NotificationLevel.INFO: "[INFO]",
        }.get(report.notification_level, "")

        return f"{prefix} Entra ID Secrets Alert - {report.get_summary()}"

    def _format_html_body(self, report: ExpirationReport) -> str:
        """Format HTML email body."""
        color = report.notification_level.color_hex

        rows = ""
        for cred in report.get_credentials_sorted_by_urgency()[:30]:
            status = cred.get_status(report.thresholds).value.upper()
            name = cred.display_name or str(cred.id)[:8]
            expiry = cred.expiry_date.strftime("%Y-%m-%d")
            portal_url = cred.azure_portal_url
            rows += f"<tr><td>{cred.application_name}</td><td>{cred.credential_type}</td>"
            rows += f"<td>{name}</td><td>{expiry}</td><td>{status}</td>"
            rows += f'<td><a href="{portal_url}" target="_blank">Manage</a></td></tr>\n'

        return f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
.header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
.summary {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
tr:nth-child(even) {{ background-color: #f2f2f2; }}
a {{ color: #0066cc; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.footer {{ margin-top: 20px; font-size: 12px; color: #6c757d; }}
</style>
</head>
<body>
<div class="header"><h1>Entra ID Secrets Alert</h1></div>
<div class="summary">
<h2>{report.get_summary()}</h2>
<p>Applications Affected: {report.affected_applications_count}</p>
<p>Expired: {report.expired_count} | Critical: {report.critical_count} | Warning: {report.warning_count}</p>
</div>
<table>
<tr><th>Application</th><th>Type</th><th>Name</th><th>Expiry</th><th>Status</th><th>Action</th></tr>
{rows}
</table>
<div class="footer"><p>Entra ID Secrets Notification System</p></div>
</body>
</html>"""
