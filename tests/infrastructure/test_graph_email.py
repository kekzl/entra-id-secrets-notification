"""Tests for Graph Email notification sender."""

from __future__ import annotations

import pytest

from src.infrastructure.adapters.notifications.graph_email import (
    GraphEmailConfig,
    GraphEmailNotificationSender,
)


class TestGraphEmailConfig:
    """Tests for GraphEmailConfig."""

    def test_default_config_disabled(self) -> None:
        """Default config should be disabled."""
        config = GraphEmailConfig()
        assert config.enabled is False
        assert config.tenant_id == ""
        assert config.client_id == ""
        assert config.client_secret == ""
        assert config.from_address == ""
        assert config.to_addresses == ""
        assert config.save_to_sent_items is False

    def test_config_is_frozen(self) -> None:
        """Config should be immutable."""
        config = GraphEmailConfig(enabled=True)
        with pytest.raises(AttributeError):
            config.enabled = False  # type: ignore[misc]


class TestGraphEmailNotificationSender:
    """Tests for GraphEmailNotificationSender."""

    def test_not_configured_when_disabled(self) -> None:
        """Sender should not be configured when disabled."""
        config = GraphEmailConfig(
            enabled=False,
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
            from_address="from@example.com",
            to_addresses="to@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is False

    def test_not_configured_without_tenant_id(self) -> None:
        """Sender should not be configured without tenant_id."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="",
            client_id="client",
            client_secret="secret",
            from_address="from@example.com",
            to_addresses="to@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is False

    def test_not_configured_without_client_id(self) -> None:
        """Sender should not be configured without client_id."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="tenant",
            client_id="",
            client_secret="secret",
            from_address="from@example.com",
            to_addresses="to@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is False

    def test_not_configured_without_from_address(self) -> None:
        """Sender should not be configured without from_address."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
            from_address="",
            to_addresses="to@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is False

    def test_not_configured_without_to_addresses(self) -> None:
        """Sender should not be configured without to_addresses."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="tenant",
            client_id="client",
            client_secret="secret",
            from_address="from@example.com",
            to_addresses="",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is False

    def test_configured_with_all_required_fields(self) -> None:
        """Sender should be configured with all required fields."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret",
            from_address="notifications@example.com",
            to_addresses="admin@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is True

    def test_configured_with_multiple_recipients(self) -> None:
        """Sender should be configured with multiple recipients."""
        config = GraphEmailConfig(
            enabled=True,
            tenant_id="tenant-id",
            client_id="client-id",
            client_secret="client-secret",
            from_address="notifications@example.com",
            to_addresses="admin@example.com,security@example.com,ops@example.com",
        )
        sender = GraphEmailNotificationSender(config)
        assert sender.is_configured() is True
