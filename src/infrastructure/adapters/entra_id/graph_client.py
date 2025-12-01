"""Microsoft Graph API client for Entra ID."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import httpx
import msal

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GraphClientConfig:
    """Configuration for Microsoft Graph API client."""

    tenant_id: str
    client_id: str
    client_secret: str
    timeout: float = 30.0


class GraphClient:
    """
    Async client for Microsoft Graph API.

    Handles authentication and paginated requests to the Graph API.
    """

    GRAPH_BASE_URL: ClassVar[str] = "https://graph.microsoft.com/v1.0"
    AUTHORITY_BASE: ClassVar[str] = "https://login.microsoftonline.com"
    SCOPE: ClassVar[list[str]] = ["https://graph.microsoft.com/.default"]

    def __init__(self, config: GraphClientConfig) -> None:
        """Initialize the Graph client."""
        self._config = config
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None
        self._msal_app: msal.ConfidentialClientApplication | None = None

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL application instance."""
        if self._msal_app is None:
            authority = f"{self.AUTHORITY_BASE}/{self._config.tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self._config.client_id,
                client_credential=self._config.client_secret,
                authority=authority,
            )
        return self._msal_app

    async def _acquire_token(self) -> str:
        """Acquire access token using client credentials flow."""
        # Check if existing token is still valid
        if self._access_token and self._token_expiry and datetime.now(UTC) < self._token_expiry:
            return self._access_token

        app = self._get_msal_app()
        result = app.acquire_token_for_client(scopes=self.SCOPE)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            msg = f"Failed to acquire access token: {error}"
            raise RuntimeError(msg)

        self._access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        # Refresh 5 minutes before expiry
        self._token_expiry = datetime.now(UTC) + timedelta(seconds=expires_in - 300)

        return self._access_token

    async def get_applications(self) -> list[dict]:
        """
        Retrieve all application registrations.

        Returns:
            List of application dictionaries from Graph API.
        """
        logger.info("Fetching application registrations from Entra ID...")
        applications = await self._get_all_pages("/applications")
        logger.info("Found %d application registrations", len(applications))
        return applications

    async def get_service_principals(self) -> list[dict]:
        """
        Retrieve all service principals.

        Returns:
            List of service principal dictionaries from Graph API.
        """
        logger.info("Fetching service principals from Entra ID...")
        service_principals = await self._get_all_pages("/servicePrincipals")
        logger.info("Found %d service principals", len(service_principals))
        return service_principals

    async def _get_all_pages(self, endpoint: str) -> list[dict]:
        """
        Retrieve all pages from a paginated Graph API endpoint.

        Args:
            endpoint: The API endpoint path.

        Returns:
            Combined list of all results across pages.
        """
        results: list[dict] = []
        url: str | None = endpoint

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            while url:
                token = await self._acquire_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                # Handle both relative and absolute URLs
                full_url = url if url.startswith("http") else f"{self.GRAPH_BASE_URL}{url}"

                response = await client.get(full_url, headers=headers)
                response.raise_for_status()
                data = response.json()

                results.extend(data.get("value", []))
                url = data.get("@odata.nextLink")

        return results
