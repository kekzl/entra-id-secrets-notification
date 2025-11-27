"""Email notification implementation."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import NotificationConfig
from .base import BaseNotifier, NotificationLevel, NotificationPayload


class EmailNotifier(BaseNotifier):
    """Send notifications via email using SMTP."""

    def __init__(self, config: NotificationConfig):
        """Initialize the email notifier."""
        super().__init__()
        self.config = config

    def is_configured(self) -> bool:
        """Check if email notification is properly configured."""
        return (
            self.config.smtp_enabled
            and bool(self.config.smtp_server)
            and bool(self.config.smtp_from)
            and bool(self.config.smtp_to)
        )

    def send(self, payload: NotificationPayload) -> bool:
        """Send an email notification."""
        if not self.is_configured():
            self.logger.warning("Email notifier is not properly configured")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = self._format_subject(payload)
            msg["From"] = self.config.smtp_from
            msg["To"] = self.config.smtp_to

            # Create plain text version
            text_content = self._format_text_body(payload)
            msg.attach(MIMEText(text_content, "plain"))

            # Create HTML version
            html_content = self._format_html_body(payload)
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            recipients = [r.strip() for r in self.config.smtp_to.split(",")]

            if self.config.smtp_use_tls:
                with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                    server.starttls()
                    if self.config.smtp_username and self.config.smtp_password:
                        server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(self.config.smtp_from, recipients, msg.as_string())
            else:
                with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                    if self.config.smtp_username and self.config.smtp_password:
                        server.login(self.config.smtp_username, self.config.smtp_password)
                    server.sendmail(self.config.smtp_from, recipients, msg.as_string())

            self.logger.info(f"Email notification sent to {self.config.smtp_to}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return False

    def _format_subject(self, payload: NotificationPayload) -> str:
        """Format the email subject line."""
        level_prefix = {
            NotificationLevel.CRITICAL: "[CRITICAL]",
            NotificationLevel.WARNING: "[WARNING]",
            NotificationLevel.INFO: "[INFO]",
        }.get(payload.level, "")

        return f"{level_prefix} Entra ID Secrets Expiration Alert - {payload.summary}"

    def _format_text_body(self, payload: NotificationPayload) -> str:
        """Format the plain text email body."""
        lines = [
            f"Entra ID Secrets Expiration Report",
            "=" * 40,
            "",
            f"Summary: {payload.summary}",
            f"Applications Affected: {payload.total_apps_affected}",
            "",
            f"Expired: {payload.expired_count}",
            f"Critical (expiring soon): {payload.critical_count}",
            f"Warning: {payload.warning_count}",
            f"Info: {payload.info_count}",
            "",
            "Details:",
            "-" * 40,
            "",
            self.format_secret_list(payload.secrets, max_items=50),
            "",
            "-" * 40,
            "This is an automated notification from the Entra ID Secrets Notification System.",
        ]
        return "\n".join(lines)

    def _format_html_body(self, payload: NotificationPayload) -> str:
        """Format the HTML email body."""
        level_color = self.get_level_color(payload.level)

        # Group secrets by category
        expired = [s for s in payload.secrets if s.is_expired]
        critical = [s for s in payload.secrets if not s.is_expired and s.days_until_expiry <= 7]
        warning = [
            s for s in payload.secrets if not s.is_expired and 7 < s.days_until_expiry <= 30
        ]
        info = [s for s in payload.secrets if not s.is_expired and s.days_until_expiry > 30]

        def format_table_rows(secrets: list, status_label: str) -> str:
            if not secrets:
                return ""
            rows = []
            for s in secrets[:20]:
                secret_name = s.display_name or s.secret_id[:8]
                expiry_str = s.expiry_date.strftime("%Y-%m-%d")
                rows.append(
                    f"<tr><td>{s.app_name}</td><td>{s.secret_type}</td>"
                    f"<td>{secret_name}</td><td>{expiry_str}</td><td>{status_label}</td></tr>"
                )
            return "\n".join(rows)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {level_color}; color: white; padding: 15px; border-radius: 5px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .stats {{ display: flex; gap: 20px; margin: 15px 0; }}
                .stat-box {{ padding: 10px 20px; border-radius: 5px; text-align: center; }}
                .expired {{ background-color: #721c24; color: white; }}
                .critical {{ background-color: #dc3545; color: white; }}
                .warning {{ background-color: #ffc107; color: black; }}
                .info {{ background-color: #17a2b8; color: white; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Entra ID Secrets Expiration Alert</h1>
            </div>

            <div class="summary">
                <h2>{payload.summary}</h2>
                <p>Applications Affected: {payload.total_apps_affected}</p>
            </div>

            <div class="stats">
                <div class="stat-box expired">Expired: {payload.expired_count}</div>
                <div class="stat-box critical">Critical: {payload.critical_count}</div>
                <div class="stat-box warning">Warning: {payload.warning_count}</div>
                <div class="stat-box info">Info: {payload.info_count}</div>
            </div>

            <table>
                <tr>
                    <th>Application</th>
                    <th>Type</th>
                    <th>Secret Name</th>
                    <th>Expiry Date</th>
                    <th>Status</th>
                </tr>
                {format_table_rows(expired, "EXPIRED")}
                {format_table_rows(critical, "CRITICAL")}
                {format_table_rows(warning, "WARNING")}
                {format_table_rows(info, "INFO")}
            </table>

            <div class="footer">
                <p>This is an automated notification from the Entra ID Secrets Notification System.</p>
            </div>
        </body>
        </html>
        """
        return html
