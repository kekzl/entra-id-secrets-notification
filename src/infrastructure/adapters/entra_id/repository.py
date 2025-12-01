"""Entra ID credential repository implementation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ....application.exceptions import CredentialRepositoryError
from ....domain.entities import Credential
from ....domain.value_objects import CredentialSource, CredentialType
from .graph_client import GraphClient, GraphClientConfig

logger = logging.getLogger(__name__)


class EntraIdCredentialRepository:
    """
    Credential repository implementation using Microsoft Graph API.

    Implements the CredentialRepository port for Entra ID.
    """

    def __init__(
        self,
        config: GraphClientConfig,
        *,
        monitor_service_principals: bool = True,
    ) -> None:
        """
        Initialize the repository.

        Args:
            config: Configuration for the Graph API client.
            monitor_service_principals: Whether to also monitor service principal credentials.
        """
        self._client = GraphClient(config)
        self._monitor_service_principals = monitor_service_principals

    async def get_all_credentials(self) -> list[Credential]:
        """
        Retrieve all credentials from Entra ID applications and service principals.

        Returns:
            List of all credentials across all applications and service principals.

        Raises:
            CredentialRepositoryError: If retrieval fails.
        """
        try:
            credentials: list[Credential] = []

            # Fetch app registration credentials
            app_credentials = await self._fetch_application_credentials()
            credentials.extend(app_credentials)

            # Fetch service principal credentials if enabled
            if self._monitor_service_principals:
                sp_credentials = await self._fetch_service_principal_credentials()
                credentials.extend(sp_credentials)

            return credentials

        except Exception as e:
            msg = f"Failed to retrieve credentials from Entra ID: {e}"
            logger.exception(msg)
            raise CredentialRepositoryError(msg) from e

    async def _fetch_application_credentials(self) -> list[Credential]:
        """Fetch credentials from app registrations."""
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
                    CredentialSource.APP_REGISTRATION,
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
                    CredentialSource.APP_REGISTRATION,
                )
                if credential:
                    credentials.append(credential)

        logger.info(
            "Retrieved %d credentials from %d app registrations",
            len(credentials),
            len(applications),
        )
        return credentials

    async def _fetch_service_principal_credentials(self) -> list[Credential]:
        """Fetch credentials from service principals."""
        service_principals = await self._client.get_service_principals()
        credentials: list[Credential] = []

        for sp in service_principals:
            sp_object_id = sp.get("id", "")
            app_id = sp.get("appId", "")
            sp_name = sp.get("displayName", "Unknown")

            # Process password credentials (secrets)
            for cred in sp.get("passwordCredentials", []):
                credential = self._map_credential(
                    cred,
                    CredentialType.PASSWORD,
                    app_id,
                    sp_name,
                    CredentialSource.SERVICE_PRINCIPAL,
                    object_id=sp_object_id,
                )
                if credential:
                    credentials.append(credential)

            # Process key credentials (certificates)
            for cred in sp.get("keyCredentials", []):
                credential = self._map_credential(
                    cred,
                    CredentialType.CERTIFICATE,
                    app_id,
                    sp_name,
                    CredentialSource.SERVICE_PRINCIPAL,
                    object_id=sp_object_id,
                )
                if credential:
                    credentials.append(credential)

        logger.info(
            "Retrieved %d credentials from %d service principals",
            len(credentials),
            len(service_principals),
        )
        return credentials

    def _map_credential(
        self,
        raw: dict[str, Any],
        credential_type: CredentialType,
        app_id: str,
        app_name: str,
        source: CredentialSource,
        *,
        object_id: str | None = None,
    ) -> Credential | None:
        """
        Map raw Graph API credential data to domain entity.

        Args:
            raw: Raw credential dictionary from Graph API.
            credential_type: Type of credential.
            app_id: Application ID.
            app_name: Application or service principal display name.
            source: Source of the credential (app registration or service principal).
            object_id: Service principal object ID (different from app ID).

        Returns:
            Credential entity or None if mapping fails.
        """
        expiry_str = raw.get("endDateTime")
        if not expiry_str:
            logger.warning(
                "Credential %s in %s %s has no expiry date",
                raw.get("keyId", "unknown"),
                source.display_name,
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
            source=source,
            object_id=object_id,
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
