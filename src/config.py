"""Configuration module for Entra ID Secrets Notification System."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AzureConfig:
    """Azure/Entra ID authentication configuration."""

    tenant_id: str = field(default_factory=lambda: os.environ.get("AZURE_TENANT_ID", ""))
    client_id: str = field(default_factory=lambda: os.environ.get("AZURE_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.environ.get("AZURE_CLIENT_SECRET", ""))

    def validate(self) -> None:
        """Validate required Azure configuration."""
        missing = []
        if not self.tenant_id:
            missing.append("AZURE_TENANT_ID")
        if not self.client_id:
            missing.append("AZURE_CLIENT_ID")
        if not self.client_secret:
            missing.append("AZURE_CLIENT_SECRET")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


@dataclass
class NotificationConfig:
    """Notification configuration."""

    # Warning thresholds in days
    critical_threshold_days: int = field(
        default_factory=lambda: int(os.environ.get("CRITICAL_THRESHOLD_DAYS", "7"))
    )
    warning_threshold_days: int = field(
        default_factory=lambda: int(os.environ.get("WARNING_THRESHOLD_DAYS", "30"))
    )
    info_threshold_days: int = field(
        default_factory=lambda: int(os.environ.get("INFO_THRESHOLD_DAYS", "90"))
    )

    # Email notification settings
    smtp_enabled: bool = field(
        default_factory=lambda: os.environ.get("SMTP_ENABLED", "false").lower() == "true"
    )
    smtp_server: str = field(default_factory=lambda: os.environ.get("SMTP_SERVER", ""))
    smtp_port: int = field(default_factory=lambda: int(os.environ.get("SMTP_PORT", "587")))
    smtp_username: str = field(default_factory=lambda: os.environ.get("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: os.environ.get("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.environ.get("SMTP_FROM", ""))
    smtp_to: str = field(default_factory=lambda: os.environ.get("SMTP_TO", ""))
    smtp_use_tls: bool = field(
        default_factory=lambda: os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    )

    # Webhook notification settings
    webhook_enabled: bool = field(
        default_factory=lambda: os.environ.get("WEBHOOK_ENABLED", "false").lower() == "true"
    )
    webhook_url: str = field(default_factory=lambda: os.environ.get("WEBHOOK_URL", ""))

    # Microsoft Teams notification settings
    teams_enabled: bool = field(
        default_factory=lambda: os.environ.get("TEAMS_ENABLED", "false").lower() == "true"
    )
    teams_webhook_url: str = field(default_factory=lambda: os.environ.get("TEAMS_WEBHOOK_URL", ""))

    # Slack notification settings
    slack_enabled: bool = field(
        default_factory=lambda: os.environ.get("SLACK_ENABLED", "false").lower() == "true"
    )
    slack_webhook_url: str = field(default_factory=lambda: os.environ.get("SLACK_WEBHOOK_URL", ""))


@dataclass
class ScheduleConfig:
    """Schedule configuration."""

    # Run mode: 'once' or 'scheduled'
    run_mode: str = field(default_factory=lambda: os.environ.get("RUN_MODE", "once"))
    # Cron expression for scheduled mode (default: daily at 8 AM)
    cron_schedule: str = field(
        default_factory=lambda: os.environ.get("CRON_SCHEDULE", "0 8 * * *")
    )


@dataclass
class AppConfig:
    """Main application configuration."""

    azure: AzureConfig = field(default_factory=AzureConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    dry_run: bool = field(
        default_factory=lambda: os.environ.get("DRY_RUN", "false").lower() == "true"
    )

    def validate(self) -> None:
        """Validate the configuration."""
        self.azure.validate()

        # Ensure at least one notification method is enabled (unless dry run)
        if not self.dry_run:
            any_enabled = (
                self.notification.smtp_enabled
                or self.notification.webhook_enabled
                or self.notification.teams_enabled
                or self.notification.slack_enabled
            )
            if not any_enabled:
                print(
                    "Warning: No notification methods enabled. "
                    "Set DRY_RUN=true or enable a notification method."
                )


def load_config() -> AppConfig:
    """Load and validate configuration from environment variables."""
    config = AppConfig()
    config.validate()
    return config
