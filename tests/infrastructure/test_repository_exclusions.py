"""Tests for EXCLUDED_APPLICATION_IDS filtering in the Entra ID repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.entities import Credential
from src.domain.value_objects import CredentialSource, CredentialType
from src.infrastructure.adapters.entra_id.repository import filter_excluded_credentials

P2P_APP_ID = UUID("a8b73557-6812-4dcd-927e-97c9e9d1c2f1")
P2P_OBJECT_ID = UUID("9130d487-8046-4f33-9efd-47a96df25482")
OTHER_APP_ID = uuid4()


def make_credential(
    *,
    application_id: UUID = P2P_APP_ID,
    object_id: UUID | None = P2P_OBJECT_ID,
    source: CredentialSource = CredentialSource.SERVICE_PRINCIPAL,
) -> Credential:
    """Build a credential for the given application / service principal."""
    return Credential(
        id=uuid4(),
        credential_type=CredentialType.CERTIFICATE,
        display_name="Test Credential",
        expiry_date=datetime.now(UTC) + timedelta(days=30),
        application_id=application_id,
        application_name="Test App",
        source=source,
        object_id=object_id,
    )


class TestFilterExcludedCredentials:
    """Exclusion matches application IDs and service principal object IDs."""

    def test_excludes_by_application_id(self) -> None:
        """Credentials of an excluded application are removed."""
        credential = make_credential()

        result = filter_excluded_credentials([credential], {str(P2P_APP_ID)})

        assert result == []

    def test_excludes_service_principal_by_object_id(self) -> None:
        """A service principal can be excluded by its object ID instead."""
        credential = make_credential()

        result = filter_excluded_credentials([credential], {str(P2P_OBJECT_ID)})

        assert result == []

    def test_matching_is_case_insensitive(self) -> None:
        """GUID casing in the exclusion list does not matter."""
        credential = make_credential()

        result = filter_excluded_credentials([credential], {str(P2P_APP_ID).upper()})

        assert result == []

    def test_unrelated_credentials_are_kept(self) -> None:
        """Credentials of other applications pass through untouched."""
        p2p = make_credential()
        other = make_credential(application_id=OTHER_APP_ID, object_id=uuid4())

        result = filter_excluded_credentials([p2p, other], {str(P2P_APP_ID)})

        assert result == [other]

    def test_empty_exclusion_set_keeps_everything(self) -> None:
        """No exclusions configured means no filtering."""
        credential = make_credential()

        result = filter_excluded_credentials([credential], set())

        assert result == [credential]
