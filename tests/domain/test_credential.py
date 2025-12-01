"""Tests for Credential entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.domain.entities import Credential
from src.domain.value_objects import CredentialType, ExpirationStatus, ExpirationThresholds


class TestCredential:
    """Tests for Credential entity."""

    def test_expired_credential_is_marked_expired(
        self, expired_credential: Credential, default_thresholds: ExpirationThresholds
    ) -> None:
        """Expired credentials should have is_expired=True."""
        assert expired_credential.is_expired is True
        assert expired_credential.days_until_expiry < 0
        assert expired_credential.get_status(default_thresholds) == ExpirationStatus.EXPIRED

    def test_critical_credential_status(
        self, critical_credential: Credential, default_thresholds: ExpirationThresholds
    ) -> None:
        """Credentials within critical threshold should have CRITICAL status."""
        assert critical_credential.is_expired is False
        assert 0 < critical_credential.days_until_expiry <= default_thresholds.critical
        assert critical_credential.get_status(default_thresholds) == ExpirationStatus.CRITICAL

    def test_warning_credential_status(
        self, warning_credential: Credential, default_thresholds: ExpirationThresholds
    ) -> None:
        """Credentials within warning threshold should have WARNING status."""
        assert warning_credential.is_expired is False
        assert warning_credential.get_status(default_thresholds) == ExpirationStatus.WARNING

    def test_healthy_credential_status(
        self, healthy_credential: Credential, default_thresholds: ExpirationThresholds
    ) -> None:
        """Healthy credentials should have HEALTHY status."""
        assert healthy_credential.is_expired is False
        assert healthy_credential.days_until_expiry > default_thresholds.info
        assert healthy_credential.get_status(default_thresholds) == ExpirationStatus.HEALTHY

    def test_requires_notification_within_info_threshold(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """Credentials within info threshold should require notification."""
        credential = Credential(
            id=uuid4(),
            credential_type=CredentialType.PASSWORD,
            display_name="Test",
            expiry_date=datetime.now(UTC) + timedelta(days=60),
            application_id=uuid4(),
            application_name="Test App",
        )
        assert credential.requires_notification(default_thresholds) is True

    def test_no_notification_for_distant_expiry(
        self, healthy_credential: Credential, default_thresholds: ExpirationThresholds
    ) -> None:
        """Credentials expiring far in the future should not require notification."""
        assert healthy_credential.requires_notification(default_thresholds) is False

    def test_create_factory_method(self) -> None:
        """Test the create factory method."""
        app_id = str(uuid4())
        cred_id = str(uuid4())
        expiry = datetime.now(UTC) + timedelta(days=30)

        credential = Credential.create(
            credential_id=cred_id,
            credential_type=CredentialType.CERTIFICATE,
            display_name="Test Cert",
            expiry_date=expiry,
            application_id=app_id,
            application_name="My App",
        )

        assert str(credential.id) == cred_id
        assert str(credential.application_id) == app_id
        assert credential.credential_type == CredentialType.CERTIFICATE
        assert credential.display_name == "Test Cert"
        assert credential.application_name == "My App"

    def test_credential_with_naive_datetime(self) -> None:
        """Credentials should handle naive datetimes by assuming UTC."""
        naive_expiry = datetime.now() + timedelta(days=10)  # noqa: DTZ005
        credential = Credential(
            id=uuid4(),
            credential_type=CredentialType.PASSWORD,
            display_name="Test",
            expiry_date=naive_expiry,
            application_id=uuid4(),
            application_name="Test App",
        )
        # Should not raise and should calculate days correctly
        assert credential.days_until_expiry >= 9
        assert credential.days_until_expiry <= 11

    def test_azure_portal_url(self) -> None:
        """Credential should provide Azure portal URL for managing the app."""
        app_id = uuid4()
        credential = Credential(
            id=uuid4(),
            credential_type=CredentialType.PASSWORD,
            display_name="Test",
            expiry_date=datetime.now(UTC) + timedelta(days=30),
            application_id=app_id,
            application_name="Test App",
        )
        expected_url = (
            f"https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps"
            f"/ApplicationMenuBlade/~/Credentials/appId/{app_id}"
        )
        assert credential.azure_portal_url == expected_url
