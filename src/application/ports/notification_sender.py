"""Port for notification sending - driven/secondary port."""

from typing import Protocol

from ...domain.entities import ExpirationReport


class NotificationSender(Protocol):
    """
    Port for sending notifications.

    This is a driven (secondary) port that defines how the application
    sends notifications to external systems.
    """

    async def send(self, report: ExpirationReport) -> bool:
        """
        Send a notification based on the expiration report.

        Args:
            report: The expiration report to notify about.

        Returns:
            True if notification was sent successfully.

        Raises:
            NotificationError: If sending fails.
        """
        ...

    def is_configured(self) -> bool:
        """
        Check if this notification sender is properly configured.

        Returns:
            True if the sender is ready to send notifications.
        """
        ...
