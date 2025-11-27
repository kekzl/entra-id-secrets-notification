"""Notification level value object."""

from enum import StrEnum, auto


class NotificationLevel(StrEnum):
    """Severity level for notifications."""

    CRITICAL = auto()
    WARNING = auto()
    INFO = auto()

    @property
    def emoji(self) -> str:
        """Get emoji representation for this level."""
        match self:
            case NotificationLevel.CRITICAL:
                return "🔴"
            case NotificationLevel.WARNING:
                return "🟡"
            case NotificationLevel.INFO:
                return "🟢"

    @property
    def color_hex(self) -> str:
        """Get hex color code for this level."""
        match self:
            case NotificationLevel.CRITICAL:
                return "#dc3545"
            case NotificationLevel.WARNING:
                return "#ffc107"
            case NotificationLevel.INFO:
                return "#17a2b8"
