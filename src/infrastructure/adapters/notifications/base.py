"""Base notification sender with common functionality."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....domain.entities import Credential, ExpirationReport


class BaseNotificationSender(ABC):
    """Abstract base class for notification senders."""

    def __init__(self) -> None:
        """Initialize the notification sender."""
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def send(self, report: ExpirationReport) -> bool:
        """Send notification for the given report."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the sender is properly configured."""
        ...

    def format_credential_list(
        self,
        credentials: list[Credential],
        *,
        max_items: int = 10,
        include_url: bool = True,
    ) -> str:
        """Format a list of credentials for display."""
        lines: list[str] = []

        for credential in credentials[:max_items]:
            status = "EXPIRED" if credential.is_expired else f"{credential.days_until_expiry}d"
            name = credential.display_name or str(credential.id)[:8]
            app_name = credential.application_name
            cred_type = credential.credential_type
            line = f"• {app_name} - {cred_type} '{name}': {status}"
            if include_url:
                line += f"\n  Manage: {credential.azure_portal_url}"
            lines.append(line)

        if len(credentials) > max_items:
            lines.append(f"... and {len(credentials) - max_items} more")

        return "\n".join(lines)
