"""Application layer exceptions."""


class ApplicationError(Exception):
    """Base exception for application errors."""


class CredentialRepositoryError(ApplicationError):
    """Raised when credential repository operations fail."""


class NotificationError(ApplicationError):
    """Raised when notification sending fails."""


class ConfigurationError(ApplicationError):
    """Raised when configuration is invalid."""
