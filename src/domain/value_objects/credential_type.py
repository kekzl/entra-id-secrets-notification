"""Credential type value object."""

from enum import StrEnum, auto


class CredentialType(StrEnum):
    """Type of credential in Entra ID application."""

    PASSWORD = auto()
    CERTIFICATE = auto()

    def __str__(self) -> str:
        return self.value
