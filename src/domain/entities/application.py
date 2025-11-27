"""Application entity representing an Entra ID app registration."""

from dataclasses import dataclass, field
from uuid import UUID

from .credential import Credential


@dataclass(slots=True)
class Application:
    """An Entra ID application registration."""

    id: UUID
    display_name: str
    credentials: list[Credential] = field(default_factory=list)

    @property
    def has_expiring_credentials(self) -> bool:
        """Check if application has any credentials requiring attention."""
        return any(cred.is_expired or cred.days_until_expiry <= 90 for cred in self.credentials)

    def add_credential(self, credential: Credential) -> None:
        """Add a credential to this application."""
        self.credentials.append(credential)
