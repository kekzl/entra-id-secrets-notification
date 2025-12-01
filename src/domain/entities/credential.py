"""Credential entity representing a secret or certificate."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from ..value_objects import CredentialType, ExpirationStatus, ExpirationThresholds


@dataclass(slots=True)
class Credential:
    """A credential (secret or certificate) belonging to an application."""

    id: UUID
    credential_type: CredentialType
    display_name: str | None
    expiry_date: datetime
    application_id: UUID
    application_name: str

    _days_until_expiry: int = field(init=False, repr=False)
    _is_expired: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Calculate derived fields."""
        now = datetime.now(UTC)
        expiry_aware = (
            self.expiry_date
            if self.expiry_date.tzinfo
            else self.expiry_date.replace(tzinfo=UTC)
        )
        delta = expiry_aware - now
        self._days_until_expiry = delta.days
        self._is_expired = delta.total_seconds() < 0

    @property
    def days_until_expiry(self) -> int:
        """Days remaining until expiration (negative if expired)."""
        return self._days_until_expiry

    @property
    def is_expired(self) -> bool:
        """Check if credential has expired."""
        return self._is_expired

    @property
    def azure_portal_url(self) -> str:
        """URL to manage this app's credentials in Azure Portal."""
        return (
            f"https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps"
            f"/ApplicationMenuBlade/~/Credentials/appId/{self.application_id}"
        )

    def get_status(self, thresholds: ExpirationThresholds) -> ExpirationStatus:
        """Determine expiration status based on thresholds."""
        if self._is_expired:
            return ExpirationStatus.EXPIRED
        if self._days_until_expiry <= thresholds.critical:
            return ExpirationStatus.CRITICAL
        if self._days_until_expiry <= thresholds.warning:
            return ExpirationStatus.WARNING
        return ExpirationStatus.HEALTHY

    def requires_notification(self, thresholds: ExpirationThresholds) -> bool:
        """Check if this credential requires notification."""
        return self._days_until_expiry <= thresholds.info

    @classmethod
    def create(
        cls,
        *,
        credential_id: str,
        credential_type: CredentialType,
        display_name: str | None,
        expiry_date: datetime,
        application_id: str,
        application_name: str,
    ) -> Self:
        """Factory method to create a Credential from raw data."""
        return cls(
            id=UUID(credential_id),
            credential_type=credential_type,
            display_name=display_name,
            expiry_date=expiry_date,
            application_id=UUID(application_id),
            application_name=application_name,
        )
