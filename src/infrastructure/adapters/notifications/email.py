"""Email notification sender using SMTP."""

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ....domain.entities import ExpirationReport
from ....domain.value_objects import NotificationLevel
from .base import BaseNotificationSender


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Email notification configuration."""

    enabled: bool = False
    server: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = ""
    to_addresses: str = ""  # Comma-separated
    use_tls: bool = True


class EmailNotificationSender(BaseNotificationSender):
    """Send notifications via SMTP email."""

    def __init__(self, config: EmailConfig) -> None:
        """Initialize the email sender."""
        super().__init__()
        self._config = config

    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return (
            self._config.enabled
            and bool(self._config.server)
            and bool(self._config.from_address)
            and bool(self._config.to_addresses)
        )

    async def send(self, report: ExpirationReport) -> bool:
        """Send email notification."""
        if not self.is_configured():
            self._logger.warning("Email sender not configured")
            return False

        try:
            msg = self._build_message(report)
            recipients = [r.strip() for r in self._config.to_addresses.split(",")]

            with smtplib.SMTP(self._config.server, self._config.port) as server:
                if self._config.use_tls:
                    server.starttls()
                if self._config.username and self._config.password:
                    server.login(self._config.username, self._config.password)
                server.sendmail(self._config.from_address, recipients, msg.as_string())

            self._logger.info("Email sent to %s", self._config.to_addresses)
            return True

        except Exception:
            self._logger.exception("Failed to send email")
            return False

    def _build_message(self, report: ExpirationReport) -> MIMEMultipart:
        """Build the email message."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._format_subject(report)
        msg["From"] = self._config.from_address
        msg["To"] = self._config.to_addresses

        text_body = self._format_text_body(report)
        html_body = self._format_html_body(report)

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        return msg

    def _format_subject(self, report: ExpirationReport) -> str:
        """Format email subject line."""
        prefix = {
            NotificationLevel.CRITICAL: "[CRITICAL]",
            NotificationLevel.WARNING: "[WARNING]",
            NotificationLevel.INFO: "[INFO]",
        }.get(report.notification_level, "")

        return f"{prefix} Entra ID Secrets Alert - {report.get_summary()}"

    def _format_text_body(self, report: ExpirationReport) -> str:
        """Format plain text email body."""
        lines = [
            "Entra ID Secrets Expiration Report",
            "=" * 40,
            "",
            f"Summary: {report.get_summary()}",
            f"Applications Affected: {report.affected_applications_count}",
            "",
            f"Expired: {report.expired_count}",
            f"Critical: {report.critical_count}",
            f"Warning: {report.warning_count}",
            "",
            "Details:",
            "-" * 40,
            "",
            self.format_credential_list(
                report.get_credentials_sorted_by_urgency(),
                max_items=50,
            ),
            "",
            "-" * 40,
            "Entra ID Secrets Notification System",
        ]
        return "\n".join(lines)

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
