"""Entra ID credential repository implementation."""

import logging
from datetime import UTC, datetime

from ....application.exceptions import CredentialRepositoryError
from ....domain.entities import Credential
from ....domain.value_objects import CredentialType
from .graph_client import GraphClient, GraphClientConfig

logger = logging.getLogger(__name__)


class EntraIdCredentialRepository:
    """
    Credential repository implementation using Microsoft Graph API.

    Implements the CredentialRepository port for Entra ID.
    """

    def __init__(self, config: GraphClientConfig) -> None:
        """
        Initialize the repository.

        Args:
            config: Configuration for the Graph API client.
        """
        self._client = GraphClient(config)

    async def get_all_credentials(self) -> list[Credential]:
        """
        Retrieve all credentials from Entra ID applications.

        Returns:
            List of all credentials across all applications.

        Raises:
            CredentialRepositoryError: If retrieval fails.
        """
        try:
            applications = await self._client.get_applications()
            credentials: list[Credential] = []

            for app in applications:
                app_id = app.get("appId", "")
                app_name = app.get("displayName", "Unknown")

                # Process password credentials (secrets)
                for cred in app.get("passwordCredentials", []):
                    credential = self._map_credential(
                        cred,
                        CredentialType.PASSWORD,
                        app_id,
                        app_name,
                    )
                    if credential:
                        credentials.append(credential)

                # Process key credentials (certificates)
                for cred in app.get("keyCredentials", []):
                    credential = self._map_credential(
                        cred,
                        CredentialType.CERTIFICATE,
                        app_id,
                        app_name,
                    )
                    if credential:
                        credentials.append(credential)

            logger.info("Retrieved %d credentials from %d applications", len(credentials), len(applications))
            return credentials

        except Exception as e:
            msg = f"Failed to retrieve credentials from Entra ID: {e}"
            logger.exception(msg)
            raise CredentialRepositoryError(msg) from e

    def _map_credential(
        self,
        raw: dict,
        credential_type: CredentialType,
        app_id: str,
        app_name: str,
    ) -> Credential | None:
        """
        Map raw Graph API credential data to domain entity.

        Args:
            raw: Raw credential dictionary from Graph API.
            credential_type: Type of credential.
            app_id: Application ID.
            app_name: Application display name.

        Returns:
            Credential entity or None if mapping fails.
        """
        expiry_str = raw.get("endDateTime")
        if not expiry_str:
            logger.warning(
                "Credential %s in app %s has no expiry date",
                raw.get("keyId", "unknown"),
                app_name,
            )
            return None

        expiry_date = self._parse_datetime(expiry_str)
        if not expiry_date:
            return None

        return Credential.create(
            credential_id=raw.get("keyId", ""),
            credential_type=credential_type,
            display_name=raw.get("displayName"),
            expiry_date=expiry_date,
            application_id=app_id,
            application_name=app_name,
        )

    @staticmethod
    def _parse_datetime(dt_string: str) -> datetime | None:
        """Parse ISO datetime string to datetime object."""
        try:
            # Handle various formats from Graph API
            dt_string = dt_string.replace("Z", "+00:00")
            dt = datetime.fromisoformat(dt_string)
            # Ensure timezone-aware
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            logger.warning("Failed to parse datetime: %s", dt_string)
            return None
