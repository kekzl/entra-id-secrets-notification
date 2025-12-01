"""Credential source value object."""

from enum import StrEnum, auto


class CredentialSource(StrEnum):
    """Source of credential in Entra ID."""

    APP_REGISTRATION = auto()
    SERVICE_PRINCIPAL = auto()

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        match self:
            case CredentialSource.APP_REGISTRATION:
                return "App Registration"
            case CredentialSource.SERVICE_PRINCIPAL:
                return "Service Principal"
