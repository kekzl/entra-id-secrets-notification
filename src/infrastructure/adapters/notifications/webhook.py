"""Generic webhook notification sender."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx

from ....domain.value_objects import CredentialSource
from .base import BaseNotificationSender

if TYPE_CHECKING:
    from ....domain.entities import Credential, ExpirationReport


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    """Webhook notification configuration."""

    enabled: bool = False
    url: str = ""


class WebhookNotificationSender(BaseNotificationSender):
    """Send notifications via generic HTTP webhook with JSON payload."""

    def __init__(self, config: WebhookConfig) -> None:
        """Initialize the webhook sender."""
        super().__init__()
        self._config = config

    def is_configured(self) -> bool:
        """Check if webhook is properly configured."""
        return self._config.enabled and bool(self._config.url)

    async def send(self, report: ExpirationReport) -> bool:
        """Send webhook notification with JSON payload."""
        if not self.is_configured():
            self._logger.warning("Webhook sender not configured")
            return False

        try:
            payload = self._build_payload(report)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._config.url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

            self._logger.info("Webhook notification sent to %s", self._config.url)
            return True

        except Exception:
            self._logger.exception("Failed to send webhook notification")
            return False

    def _build_payload(self, report: ExpirationReport) -> dict:
        """Build the JSON payload for the webhook."""
        app_creds = report.get_credentials_by_source(CredentialSource.APP_REGISTRATION)
        sp_creds = report.get_credentials_by_source(CredentialSource.SERVICE_PRINCIPAL)

        return {
            "event_type": "entra_id_secrets_alert",
            "timestamp": datetime.now(UTC).isoformat(),
            "level": report.notification_level.value,
            "summary": report.get_summary(),
            "statistics": {
                "total_applications_affected": report.affected_applications_count,
                "total_credentials": report.total_count,
                "expired_count": report.expired_count,
                "critical_count": report.critical_count,
                "warning_count": report.warning_count,
                "healthy_count": report.healthy_count,
            },
            "app_registrations": {
                "summary": report.get_source_summary(CredentialSource.APP_REGISTRATION),
                "counts": report.get_source_counts(CredentialSource.APP_REGISTRATION),
                "credentials": self._format_credentials(report, app_creds),
            },
            "service_principals": {
                "summary": report.get_source_summary(CredentialSource.SERVICE_PRINCIPAL),
                "counts": report.get_source_counts(CredentialSource.SERVICE_PRINCIPAL),
                "credentials": self._format_credentials(report, sp_creds),
            },
            # Keep legacy field for backward compatibility
            "credentials": self._format_credentials(report, report.get_credentials_sorted_by_urgency()),
        }

    def _format_credentials(self, report: ExpirationReport, credentials: list[Credential]) -> list[dict]:
        """Format credentials list for JSON payload."""
        return [
            {
                "application_id": str(cred.application_id),
                "application_name": cred.application_name,
                "credential_id": str(cred.id),
                "credential_type": str(cred.credential_type),
                "display_name": cred.display_name,
                "expiry_date": cred.expiry_date.isoformat(),
                "days_until_expiry": cred.days_until_expiry,
                "is_expired": cred.is_expired,
                "status": cred.get_status(report.thresholds).value,
                "source": str(cred.source),
                "azure_portal_url": cred.azure_portal_url,
            }
            for cred in credentials
        ]
