"""Expiration report aggregate root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..value_objects import ExpirationStatus, ExpirationThresholds, NotificationLevel
from .credential import Credential


@dataclass(slots=True)
class ExpirationReport:
    """Aggregate root representing an expiration check report."""

    credentials: list[Credential]
    thresholds: ExpirationThresholds
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    _categorized: dict[ExpirationStatus, list[Credential]] = field(
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        """Categorize credentials by status."""
        self._categorized = {status: [] for status in ExpirationStatus}
        for credential in self.credentials:
            status = credential.get_status(self.thresholds)
            self._categorized[status].append(credential)

    @property
    def expired(self) -> list[Credential]:
        """Get all expired credentials."""
        return self._categorized[ExpirationStatus.EXPIRED]

    @property
    def critical(self) -> list[Credential]:
        """Get credentials in critical state."""
        return self._categorized[ExpirationStatus.CRITICAL]

    @property
    def warning(self) -> list[Credential]:
        """Get credentials in warning state."""
        return self._categorized[ExpirationStatus.WARNING]

    @property
    def healthy(self) -> list[Credential]:
        """Get healthy credentials."""
        return self._categorized[ExpirationStatus.HEALTHY]

    @property
    def expired_count(self) -> int:
        """Count of expired credentials."""
        return len(self.expired)

    @property
    def critical_count(self) -> int:
        """Count of critical credentials."""
        return len(self.critical)

    @property
    def warning_count(self) -> int:
        """Count of warning credentials."""
        return len(self.warning)

    @property
    def healthy_count(self) -> int:
        """Count of healthy credentials."""
        return len(self.healthy)

    @property
    def total_count(self) -> int:
        """Total credential count."""
        return len(self.credentials)

    @property
    def affected_applications_count(self) -> int:
        """Count of unique applications with credentials requiring attention."""
        requiring_attention = [
            c for c in self.credentials
            if c.get_status(self.thresholds).requires_attention
        ]
        return len({c.application_id for c in requiring_attention})

    @property
    def notification_level(self) -> NotificationLevel:
        """Determine the overall notification level for this report."""
        if self.expired or self.critical:
            return NotificationLevel.CRITICAL
        if self.warning:
            return NotificationLevel.WARNING
        return NotificationLevel.INFO

    @property
    def requires_notification(self) -> bool:
        """Check if this report warrants sending a notification."""
        return bool(self.expired or self.critical or self.warning)

    def get_summary(self) -> str:
        """Generate a human-readable summary of the report."""
        parts: list[str] = []
        if self.expired_count:
            parts.append(f"{self.expired_count} expired")
        if self.critical_count:
            parts.append(f"{self.critical_count} critical")
        if self.warning_count:
            parts.append(f"{self.warning_count} warning")
        if self.healthy_count:
            parts.append(f"{self.healthy_count} healthy")

        total_attention = self.expired_count + self.critical_count + self.warning_count
        if not total_attention:
            return "All credentials are healthy"

        return f"{total_attention} credentials requiring attention: {', '.join(parts)}"

    def get_credentials_sorted_by_urgency(self) -> list[Credential]:
        """Get all credentials sorted by urgency (most urgent first)."""
        return sorted(self.credentials, key=lambda c: c.days_until_expiry)
