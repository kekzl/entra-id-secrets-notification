"""Tests for mirrored-credential deduplication in the Entra ID repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.entities import Credential
from src.domain.value_objects import CredentialSource, CredentialType
from src.infrastructure.adapters.entra_id.repository import deduplicate_credentials

APP_ID = uuid4()
SP_OBJECT_ID = uuid4()
KEY_ID = uuid4()


def make_credential(
    *,
    key_id: UUID = KEY_ID,
    credential_type: CredentialType,
    source: CredentialSource = CredentialSource.SERVICE_PRINCIPAL,
    object_id: UUID | None = SP_OBJECT_ID,
    display_name: str | None = "CN=MS-Organization-P2P-Access [2025]",
) -> Credential:
    """Build a credential with a fixed keyId."""
    return Credential(
        id=key_id,
        credential_type=credential_type,
        display_name=display_name,
        expiry_date=datetime.now(UTC) + timedelta(days=30),
        application_id=APP_ID,
        application_name="P2P Server",
        source=source,
        object_id=object_id,
    )


class TestDeduplicateCredentials:
    """The same keyId listed as password and certificate counts once."""

    def test_mirrored_certificate_counts_once(self) -> None:
        """Graph returns P2P certificates in both collections with one keyId."""
        password_entry = make_credential(credential_type=CredentialType.PASSWORD)
        certificate_entry = make_credential(credential_type=CredentialType.CERTIFICATE)

        result = deduplicate_credentials([password_entry, certificate_entry])

        assert len(result) == 1
        assert result[0].credential_type is CredentialType.CERTIFICATE

    def test_dedupe_is_order_independent(self) -> None:
        """Certificate representation wins regardless of input order."""
        password_entry = make_credential(credential_type=CredentialType.PASSWORD)
        certificate_entry = make_credential(credential_type=CredentialType.CERTIFICATE)

        result = deduplicate_credentials([certificate_entry, password_entry])

        assert len(result) == 1
        assert result[0].credential_type is CredentialType.CERTIFICATE

    def test_distinct_key_ids_are_kept(self) -> None:
        """Different keyIds are different credentials, even with equal names."""
        first = make_credential(key_id=uuid4(), credential_type=CredentialType.CERTIFICATE)
        second = make_credential(key_id=uuid4(), credential_type=CredentialType.CERTIFICATE)

        result = deduplicate_credentials([first, second])

        assert len(result) == 2

    def test_same_key_id_across_sources_is_kept(self) -> None:
        """App-registration and service-principal views stay separate."""
        app_entry = make_credential(
            credential_type=CredentialType.CERTIFICATE,
            source=CredentialSource.APP_REGISTRATION,
            object_id=None,
        )
        sp_entry = make_credential(credential_type=CredentialType.CERTIFICATE)

        result = deduplicate_credentials([app_entry, sp_entry])

        assert len(result) == 2
