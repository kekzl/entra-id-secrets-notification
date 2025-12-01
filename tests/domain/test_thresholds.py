"""Tests for ExpirationThresholds value object."""

from __future__ import annotations

import pytest

from src.domain.value_objects import ExpirationThresholds


class TestExpirationThresholds:
    """Tests for ExpirationThresholds value object."""

    def test_default_thresholds(self) -> None:
        """Default thresholds should be 7, 30, 90 days."""
        thresholds = ExpirationThresholds()
        assert thresholds.critical == 7
        assert thresholds.warning == 30
        assert thresholds.info == 90

    def test_custom_thresholds(self) -> None:
        """Custom thresholds should be accepted if valid."""
        thresholds = ExpirationThresholds(critical=14, warning=60, info=120)
        assert thresholds.critical == 14
        assert thresholds.warning == 60
        assert thresholds.info == 120

    def test_invalid_thresholds_order(self) -> None:
        """Thresholds must be in order: critical < warning < info."""
        with pytest.raises(ValueError, match="Thresholds must be"):
            ExpirationThresholds(critical=30, warning=7, info=90)

    def test_critical_greater_than_warning(self) -> None:
        """Critical cannot be greater than warning."""
        with pytest.raises(ValueError, match="Thresholds must be"):
            ExpirationThresholds(critical=40, warning=30, info=90)

    def test_warning_greater_than_info(self) -> None:
        """Warning cannot be greater than info."""
        with pytest.raises(ValueError, match="Thresholds must be"):
            ExpirationThresholds(critical=7, warning=100, info=90)

    def test_zero_critical_invalid(self) -> None:
        """Critical threshold cannot be zero."""
        with pytest.raises(ValueError, match="Thresholds must be"):
            ExpirationThresholds(critical=0, warning=30, info=90)

    def test_negative_threshold_invalid(self) -> None:
        """Negative thresholds are invalid."""
        with pytest.raises(ValueError, match="Thresholds must be"):
            ExpirationThresholds(critical=-1, warning=30, info=90)

    def test_thresholds_are_frozen(self) -> None:
        """Thresholds should be immutable."""
        thresholds = ExpirationThresholds()
        with pytest.raises(AttributeError):
            thresholds.critical = 10  # type: ignore[misc]
