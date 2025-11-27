"""Microsoft Graph API client for Entra ID application secrets."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import msal
import requests

from .config import AzureConfig

logger = logging.getLogger(__name__)


@dataclass
class SecretInfo:
    """Information about an application secret or certificate."""

    app_id: str
    app_name: str
    secret_id: str
    secret_type: str  # 'password' or 'certificate'
    display_name: Optional[str]
    expiry_date: datetime
    days_until_expiry: int
    is_expired: bool


class GraphClient:
    """Microsoft Graph API client for fetching application secrets."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    SCOPE = ["https://graph.microsoft.com/.default"]

    def __init__(self, config: AzureConfig):
        """Initialize the Graph client with Azure configuration."""
        self.config = config
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_access_token(self) -> str:
        """Get an access token using client credentials flow."""
        if self._access_token and self._token_expiry:
            if datetime.now(timezone.utc) < self._token_expiry:
                return self._access_token

        authority = f"https://login.microsoftonline.com/{self.config.tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=self.config.client_id,
            client_credential=self.config.client_secret,
            authority=authority,
        )

        result = app.acquire_token_for_client(scopes=self.SCOPE)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise RuntimeError(f"Failed to acquire access token: {error}")

        self._access_token = result["access_token"]
        # Token usually expires in 1 hour, refresh 5 minutes before
        expires_in = result.get("expires_in", 3600)
        self._token_expiry = datetime.now(timezone.utc).replace(
            microsecond=0
        ) + __import__("datetime").timedelta(seconds=expires_in - 300)

        return self._access_token

    def _make_request(self, endpoint: str) -> dict:
        """Make an authenticated request to the Graph API."""
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.GRAPH_BASE_URL}{endpoint}"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get_all_pages(self, endpoint: str) -> list:
        """Get all pages of results from a paginated endpoint."""
        results = []
        url = endpoint

        while url:
            if url.startswith("http"):
                # Full URL from @odata.nextLink
                token = self._get_access_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
            else:
                data = self._make_request(url)

            results.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

        return results

    def get_applications(self) -> list[dict]:
        """Get all application registrations in the tenant."""
        logger.info("Fetching application registrations from Entra ID...")
        apps = self._get_all_pages("/applications")
        logger.info(f"Found {len(apps)} application registrations")
        return apps

    def get_expiring_secrets(self) -> list[SecretInfo]:
        """Get all secrets and certificates with their expiry information."""
        applications = self.get_applications()
        secrets: list[SecretInfo] = []
        now = datetime.now(timezone.utc)

        for app in applications:
            app_id = app.get("appId", "")
            app_name = app.get("displayName", "Unknown")

            # Check password credentials (secrets)
            for cred in app.get("passwordCredentials", []):
                expiry = self._parse_datetime(cred.get("endDateTime"))
                if expiry:
                    days_until = (expiry - now).days
                    secrets.append(
                        SecretInfo(
                            app_id=app_id,
                            app_name=app_name,
                            secret_id=cred.get("keyId", ""),
                            secret_type="password",
                            display_name=cred.get("displayName"),
                            expiry_date=expiry,
                            days_until_expiry=days_until,
                            is_expired=days_until < 0,
                        )
                    )

            # Check key credentials (certificates)
            for cred in app.get("keyCredentials", []):
                expiry = self._parse_datetime(cred.get("endDateTime"))
                if expiry:
                    days_until = (expiry - now).days
                    secrets.append(
                        SecretInfo(
                            app_id=app_id,
                            app_name=app_name,
                            secret_id=cred.get("keyId", ""),
                            secret_type="certificate",
                            display_name=cred.get("displayName"),
                            expiry_date=expiry,
                            days_until_expiry=days_until,
                            is_expired=days_until < 0,
                        )
                    )

        logger.info(f"Found {len(secrets)} total secrets and certificates")
        return secrets

    @staticmethod
    def _parse_datetime(dt_string: Optional[str]) -> Optional[datetime]:
        """Parse an ISO datetime string to a datetime object."""
        if not dt_string:
            return None
        try:
            # Handle various datetime formats from Graph API
            dt_string = dt_string.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_string)
        except ValueError:
            logger.warning(f"Failed to parse datetime: {dt_string}")
            return None
