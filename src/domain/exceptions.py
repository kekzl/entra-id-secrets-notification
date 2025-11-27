"""Domain exceptions."""


class DomainError(Exception):
    """Base exception for domain errors."""


class CredentialNotFoundError(DomainError):
    """Raised when a credential is not found."""


class InvalidThresholdsError(DomainError):
    """Raised when thresholds are invalid."""


class ReportGenerationError(DomainError):
    """Raised when report generation fails."""
