"""Application settings loaded from environment variables."""

import os
from dataclasses import dataclass, field
from functools import cached_property

from ...domain.value_objects import ExpirationThresholds
from ..adapters.entra_id.graph_client import GraphClientConfig
from ..adapters.notifications.email import EmailConfig
from ..adapters.notifications.graph_email import GraphEmailConfig
from ..adapters.notifications.slack import SlackConfig
from ..adapters.notifications.teams import TeamsConfig
from ..adapters.notifications.webhook import WebhookConfig


def _env_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment variable."""
    return os.environ.get(key, str(default)).lower() in ("true", "1", "yes")


def _env_int(key: str, default: int) -> int:
    """Get integer from environment variable."""
    return int(os.environ.get(key, str(default)))


def _env_str(key: str, default: str = "") -> str:
    """Get string from environment variable."""
    return os.environ.get(key, default)


@dataclass
class Settings:
    """Application settings container."""

    # Azure/Entra ID
    azure_tenant_id: str = field(default_factory=lambda: _env_str("AZURE_TENANT_ID"))
    azure_client_id: str = field(default_factory=lambda: _env_str("AZURE_CLIENT_ID"))
    azure_client_secret: str = field(default_factory=lambda: _env_str("AZURE_CLIENT_SECRET"))

    # Thresholds
    critical_threshold_days: int = field(default_factory=lambda: _env_int("CRITICAL_THRESHOLD_DAYS", 7))
    warning_threshold_days: int = field(default_factory=lambda: _env_int("WARNING_THRESHOLD_DAYS", 30))
    info_threshold_days: int = field(default_factory=lambda: _env_int("INFO_THRESHOLD_DAYS", 90))

    # Run configuration
    run_mode: str = field(default_factory=lambda: _env_str("RUN_MODE", "once"))
    cron_schedule: str = field(default_factory=lambda: _env_str("CRON_SCHEDULE", "0 8 * * *"))
    log_level: str = field(default_factory=lambda: _env_str("LOG_LEVEL", "INFO"))
    dry_run: bool = field(default_factory=lambda: _env_bool("DRY_RUN"))

    # Email settings
    smtp_enabled: bool = field(default_factory=lambda: _env_bool("SMTP_ENABLED"))
    smtp_server: str = field(default_factory=lambda: _env_str("SMTP_SERVER"))
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 587))
    smtp_username: str = field(default_factory=lambda: _env_str("SMTP_USERNAME"))
    smtp_password: str = field(default_factory=lambda: _env_str("SMTP_PASSWORD"))
    smtp_from: str = field(default_factory=lambda: _env_str("SMTP_FROM"))
    smtp_to: str = field(default_factory=lambda: _env_str("SMTP_TO"))
    smtp_use_tls: bool = field(default_factory=lambda: _env_bool("SMTP_USE_TLS", default=True))

    # Teams settings
    teams_enabled: bool = field(default_factory=lambda: _env_bool("TEAMS_ENABLED"))
    teams_webhook_url: str = field(default_factory=lambda: _env_str("TEAMS_WEBHOOK_URL"))

    # Slack settings
    slack_enabled: bool = field(default_factory=lambda: _env_bool("SLACK_ENABLED"))
    slack_webhook_url: str = field(default_factory=lambda: _env_str("SLACK_WEBHOOK_URL"))

    # Webhook settings
    webhook_enabled: bool = field(default_factory=lambda: _env_bool("WEBHOOK_ENABLED"))
    webhook_url: str = field(default_factory=lambda: _env_str("WEBHOOK_URL"))

    # Graph email settings (MS Graph API)
    graph_email_enabled: bool = field(default_factory=lambda: _env_bool("GRAPH_EMAIL_ENABLED"))
    graph_email_tenant_id: str = field(default_factory=lambda: _env_str("GRAPH_EMAIL_TENANT_ID"))
    graph_email_client_id: str = field(default_factory=lambda: _env_str("GRAPH_EMAIL_CLIENT_ID"))
    graph_email_client_secret: str = field(default_factory=lambda: _env_str("GRAPH_EMAIL_CLIENT_SECRET"))
    graph_email_from: str = field(default_factory=lambda: _env_str("GRAPH_EMAIL_FROM"))
    graph_email_to: str = field(default_factory=lambda: _env_str("GRAPH_EMAIL_TO"))
    graph_email_save_to_sent: bool = field(default_factory=lambda: _env_bool("GRAPH_EMAIL_SAVE_TO_SENT"))

    # API settings
    api_enabled: bool = field(default_factory=lambda: _env_bool("API_ENABLED"))
    api_host: str = field(default_factory=lambda: _env_str("API_HOST", "0.0.0.0"))  # noqa: S104
    api_port: int = field(default_factory=lambda: _env_int("API_PORT", 8080))

    def validate(self) -> None:
        """Validate required settings."""
        missing: list[str] = []

        if not self.azure_tenant_id:
            missing.append("AZURE_TENANT_ID")
        if not self.azure_client_id:
            missing.append("AZURE_CLIENT_ID")
        if not self.azure_client_secret:
            missing.append("AZURE_CLIENT_SECRET")

        if missing:
            msg = f"Missing required environment variables: {', '.join(missing)}"
            raise ValueError(msg)

    @cached_property
    def graph_config(self) -> GraphClientConfig:
        """Get Graph API client configuration."""
        return GraphClientConfig(
            tenant_id=self.azure_tenant_id,
            client_id=self.azure_client_id,
            client_secret=self.azure_client_secret,
        )

    @cached_property
    def thresholds(self) -> ExpirationThresholds:
        """Get expiration thresholds."""
        return ExpirationThresholds(
            critical=self.critical_threshold_days,
            warning=self.warning_threshold_days,
            info=self.info_threshold_days,
        )

    @cached_property
    def email_config(self) -> EmailConfig:
        """Get email configuration."""
        return EmailConfig(
            enabled=self.smtp_enabled,
            server=self.smtp_server,
            port=self.smtp_port,
            username=self.smtp_username,
            password=self.smtp_password,
            from_address=self.smtp_from,
            to_addresses=self.smtp_to,
            use_tls=self.smtp_use_tls,
        )

    @cached_property
    def teams_config(self) -> TeamsConfig:
        """Get Teams configuration."""
        return TeamsConfig(
            enabled=self.teams_enabled,
            webhook_url=self.teams_webhook_url,
        )

    @cached_property
    def slack_config(self) -> SlackConfig:
        """Get Slack configuration."""
        return SlackConfig(
            enabled=self.slack_enabled,
            webhook_url=self.slack_webhook_url,
        )

    @cached_property
    def webhook_config(self) -> WebhookConfig:
        """Get webhook configuration."""
        return WebhookConfig(
            enabled=self.webhook_enabled,
            url=self.webhook_url,
        )

    @cached_property
    def graph_email_config(self) -> GraphEmailConfig:
        """Get Graph email configuration."""
        # Use main Azure credentials if Graph-specific ones not provided
        tenant_id = self.graph_email_tenant_id or self.azure_tenant_id
        client_id = self.graph_email_client_id or self.azure_client_id
        client_secret = self.graph_email_client_secret or self.azure_client_secret

        return GraphEmailConfig(
            enabled=self.graph_email_enabled,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            from_address=self.graph_email_from,
            to_addresses=self.graph_email_to,
            save_to_sent_items=self.graph_email_save_to_sent,
        )


def load_settings() -> Settings:
    """Load and validate settings from environment."""
    settings = Settings()
    settings.validate()
    return settings
