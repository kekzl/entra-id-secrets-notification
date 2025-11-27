"""Application ports - Interfaces for external adapters."""

from .credential_repository import CredentialRepository
from .notification_sender import NotificationSender

__all__ = [
    "CredentialRepository",
    "NotificationSender",
]
