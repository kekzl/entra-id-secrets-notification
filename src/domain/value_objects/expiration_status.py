"""Expiration status value object."""

from enum import StrEnum, auto


class ExpirationStatus(StrEnum):
    """Status of a credential based on expiration."""

    EXPIRED = auto()
    CRITICAL = auto()
    WARNING = auto()
    HEALTHY = auto()

    @property
    def requires_attention(self) -> bool:
        """Check if this status requires attention."""
        return self in {ExpirationStatus.EXPIRED, ExpirationStatus.CRITICAL, ExpirationStatus.WARNING}

    def __str__(self) -> str:
        return self.value
