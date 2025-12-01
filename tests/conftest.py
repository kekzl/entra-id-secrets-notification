"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.entities import Credential
from src.domain.value_objects import CredentialType, ExpirationThresholds


@pytest.fixture
def default_thresholds() -> ExpirationThresholds:
    """Default expiration thresholds."""
    return ExpirationThresholds(critical=7, warning=30, info=90)


@pytest.fixture
def expired_credential() -> Credential:
    """A credential that has already expired."""
    return Credential(
        id=uuid4(),
        credential_type=CredentialType.PASSWORD,
        display_name="Expired Secret",
        expiry_date=datetime.now(UTC) - timedelta(days=5),
        application_id=uuid4(),
        application_name="Test App",
    )


@pytest.fixture
def critical_credential() -> Credential:
    """A credential expiring within critical threshold."""
    return Credential(
        id=uuid4(),
        credential_type=CredentialType.PASSWORD,
        display_name="Critical Secret",
        expiry_date=datetime.now(UTC) + timedelta(days=3),
        application_id=uuid4(),
        application_name="Test App",
    )


@pytest.fixture
def warning_credential() -> Credential:
    """A credential expiring within warning threshold."""
    return Credential(
        id=uuid4(),
        credential_type=CredentialType.CERTIFICATE,
        display_name="Warning Cert",
        expiry_date=datetime.now(UTC) + timedelta(days=15),
        application_id=uuid4(),
        application_name="Test App",
    )


@pytest.fixture
def healthy_credential() -> Credential:
    """A healthy credential not expiring soon."""
    return Credential(
        id=uuid4(),
        credential_type=CredentialType.CERTIFICATE,
        display_name="Healthy Cert",
        expiry_date=datetime.now(UTC) + timedelta(days=180),
        application_id=uuid4(),
        application_name="Test App",
    )
