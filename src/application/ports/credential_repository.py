"""Port for credential repository - driven/secondary port."""

from typing import Protocol

from ...domain.entities import Credential


class CredentialRepository(Protocol):
    """
    Port for retrieving credentials from external systems.

    This is a driven (secondary) port that defines how the application
    retrieves credential information from external identity providers.
    """

    async def get_all_credentials(self) -> list[Credential]:
        """
        Retrieve all credentials from the identity provider.

        Returns:
            List of all credentials across all applications.

        Raises:
            CredentialRepositoryError: If retrieval fails.
        """
        ...
