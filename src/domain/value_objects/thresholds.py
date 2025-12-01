"""Expiration thresholds value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExpirationThresholds:
    """Thresholds for determining expiration status (in days)."""

    critical: int = 7
    warning: int = 30
    info: int = 90

    def __post_init__(self) -> None:
        """Validate thresholds are in correct order."""
        if not (0 < self.critical < self.warning < self.info):
            msg = (
                f"Thresholds must be: 0 < critical({self.critical}) "
                f"< warning({self.warning}) < info({self.info})"
            )
            raise ValueError(msg)
