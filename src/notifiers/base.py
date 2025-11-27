"""Base notifier class and notification types."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph_client import SecretInfo

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification severity levels."""

    CRITICAL = "critical"  # Expired or expiring very soon
    WARNING = "warning"  # Expiring soon
    INFO = "info"  # Expiring in the future


@dataclass
class NotificationPayload:
    """Payload for notifications."""

    level: NotificationLevel
    title: str
    summary: str
    secrets: list["SecretInfo"]
    total_apps_affected: int
    critical_count: int
    warning_count: int
    info_count: int
    expired_count: int


class BaseNotifier(ABC):
    """Base class for notification implementations."""

    def __init__(self):
        """Initialize the notifier."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def send(self, payload: NotificationPayload) -> bool:
        """
        Send a notification.

        Args:
            payload: The notification payload to send.

        Returns:
            True if the notification was sent successfully, False otherwise.
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the notifier is properly configured.

        Returns:
            True if the notifier is ready to send notifications.
        """
        pass

    def format_secret_list(
        self, secrets: list["SecretInfo"], max_items: int = 10
    ) -> str:
        """
        Format a list of secrets for display.

        Args:
            secrets: List of secrets to format.
            max_items: Maximum number of items to include.

        Returns:
            Formatted string representation.
        """
        lines = []
        for secret in secrets[:max_items]:
            status = "EXPIRED" if secret.is_expired else f"{secret.days_until_expiry} days"
            secret_name = secret.display_name or secret.secret_id[:8]
            lines.append(
                f"• {secret.app_name} - {secret.secret_type} '{secret_name}': {status}"
            )

        if len(secrets) > max_items:
            lines.append(f"... and {len(secrets) - max_items} more")

        return "\n".join(lines)

    def get_level_emoji(self, level: NotificationLevel) -> str:
        """Get an emoji for a notification level."""
        return {
            NotificationLevel.CRITICAL: "🔴",
            NotificationLevel.WARNING: "🟡",
            NotificationLevel.INFO: "🟢",
        }.get(level, "⚪")

    def get_level_color(self, level: NotificationLevel) -> str:
        """Get a color code for a notification level."""
        return {
            NotificationLevel.CRITICAL: "#dc3545",  # Red
            NotificationLevel.WARNING: "#ffc107",  # Yellow
            NotificationLevel.INFO: "#17a2b8",  # Blue
        }.get(level, "#6c757d")  # Gray
