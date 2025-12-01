"""Tests for ExpirationStatus value object."""

from __future__ import annotations

from src.domain.value_objects import ExpirationStatus


class TestExpirationStatus:
    """Tests for ExpirationStatus enum."""

    def test_expired_requires_attention(self) -> None:
        """EXPIRED status should require attention."""
        assert ExpirationStatus.EXPIRED.requires_attention is True

    def test_critical_requires_attention(self) -> None:
        """CRITICAL status should require attention."""
        assert ExpirationStatus.CRITICAL.requires_attention is True

    def test_warning_requires_attention(self) -> None:
        """WARNING status should require attention."""
        assert ExpirationStatus.WARNING.requires_attention is True

    def test_healthy_does_not_require_attention(self) -> None:
        """HEALTHY status should not require attention."""
        assert ExpirationStatus.HEALTHY.requires_attention is False

    def test_status_string_representation(self) -> None:
        """Status should have string representation."""
        assert str(ExpirationStatus.EXPIRED) == "expired"
        assert str(ExpirationStatus.CRITICAL) == "critical"
        assert str(ExpirationStatus.WARNING) == "warning"
        assert str(ExpirationStatus.HEALTHY) == "healthy"

    def test_status_values(self) -> None:
        """Status enum values should be lowercase strings."""
        assert ExpirationStatus.EXPIRED.value == "expired"
        assert ExpirationStatus.CRITICAL.value == "critical"
        assert ExpirationStatus.WARNING.value == "warning"
        assert ExpirationStatus.HEALTHY.value == "healthy"
