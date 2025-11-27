#!/usr/bin/env python3
"""
Entra ID Secrets Notification System

Main entry point for the application that monitors Azure AD/Entra ID
application secrets and certificates for expiration and sends notifications.
"""

import logging
import sys
import time
from datetime import datetime, timezone

from croniter import croniter

from .config import AppConfig, load_config
from .graph_client import GraphClient, SecretInfo
from .notifiers import (
    BaseNotifier,
    EmailNotifier,
    NotificationLevel,
    SlackNotifier,
    TeamsNotifier,
    WebhookNotifier,
)
from .notifiers.base import NotificationPayload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class SecretsNotificationService:
    """Main service class for secrets notification."""

    def __init__(self, config: AppConfig):
        """Initialize the service with configuration."""
        self.config = config
        self.graph_client = GraphClient(config.azure)
        self.notifiers: list[BaseNotifier] = self._initialize_notifiers()

    def _initialize_notifiers(self) -> list[BaseNotifier]:
        """Initialize all configured notifiers."""
        notifiers = []

        email = EmailNotifier(self.config.notification)
        if email.is_configured():
            notifiers.append(email)
            logger.info("Email notifier enabled")

        teams = TeamsNotifier(self.config.notification)
        if teams.is_configured():
            notifiers.append(teams)
            logger.info("Teams notifier enabled")

        slack = SlackNotifier(self.config.notification)
        if slack.is_configured():
            notifiers.append(slack)
            logger.info("Slack notifier enabled")

        webhook = WebhookNotifier(self.config.notification)
        if webhook.is_configured():
            notifiers.append(webhook)
            logger.info("Webhook notifier enabled")

        return notifiers

    def check_secrets(self) -> list[SecretInfo]:
        """Check all secrets and return those that need attention."""
        all_secrets = self.graph_client.get_expiring_secrets()

        # Filter secrets based on thresholds
        relevant_secrets = [
            s
            for s in all_secrets
            if s.days_until_expiry <= self.config.notification.info_threshold_days
        ]

        return sorted(relevant_secrets, key=lambda s: s.days_until_expiry)

    def categorize_secrets(
        self, secrets: list[SecretInfo]
    ) -> tuple[list[SecretInfo], list[SecretInfo], list[SecretInfo], list[SecretInfo]]:
        """
        Categorize secrets by severity.

        Returns:
            Tuple of (expired, critical, warning, info) lists
        """
        expired = []
        critical = []
        warning = []
        info = []

        critical_days = self.config.notification.critical_threshold_days
        warning_days = self.config.notification.warning_threshold_days

        for secret in secrets:
            if secret.is_expired:
                expired.append(secret)
            elif secret.days_until_expiry <= critical_days:
                critical.append(secret)
            elif secret.days_until_expiry <= warning_days:
                warning.append(secret)
            else:
                info.append(secret)

        return expired, critical, warning, info

    def build_notification_payload(self, secrets: list[SecretInfo]) -> NotificationPayload:
        """Build a notification payload from the secrets."""
        expired, critical, warning, info = self.categorize_secrets(secrets)

        # Determine overall level
        if expired or critical:
            level = NotificationLevel.CRITICAL
        elif warning:
            level = NotificationLevel.WARNING
        else:
            level = NotificationLevel.INFO

        # Count unique applications
        unique_apps = set(s.app_id for s in secrets)

        # Build summary
        parts = []
        if expired:
            parts.append(f"{len(expired)} expired")
        if critical:
            parts.append(f"{len(critical)} critical")
        if warning:
            parts.append(f"{len(warning)} warning")
        if info:
            parts.append(f"{len(info)} info")

        summary = f"{len(secrets)} secrets/certificates requiring attention: " + ", ".join(parts)

        return NotificationPayload(
            level=level,
            title="Entra ID Secrets Expiration Alert",
            summary=summary,
            secrets=secrets,
            total_apps_affected=len(unique_apps),
            expired_count=len(expired),
            critical_count=len(critical),
            warning_count=len(warning),
            info_count=len(info),
        )

    def send_notifications(self, payload: NotificationPayload) -> bool:
        """Send notifications through all configured notifiers."""
        if self.config.dry_run:
            logger.info("DRY RUN: Would send notification:")
            logger.info(f"  Level: {payload.level.value}")
            logger.info(f"  Summary: {payload.summary}")
            logger.info(f"  Apps affected: {payload.total_apps_affected}")
            logger.info(f"  Expired: {payload.expired_count}")
            logger.info(f"  Critical: {payload.critical_count}")
            logger.info(f"  Warning: {payload.warning_count}")
            logger.info(f"  Info: {payload.info_count}")
            return True

        if not self.notifiers:
            logger.warning("No notifiers configured, skipping notification")
            return False

        success = True
        for notifier in self.notifiers:
            try:
                if not notifier.send(payload):
                    success = False
            except Exception as e:
                logger.error(f"Error sending notification via {notifier.__class__.__name__}: {e}")
                success = False

        return success

    def run_check(self) -> bool:
        """Run a single check and send notifications if needed."""
        logger.info("Starting secrets expiration check...")

        try:
            secrets = self.check_secrets()

            if not secrets:
                logger.info("No secrets found requiring attention")
                return True

            logger.info(f"Found {len(secrets)} secrets requiring attention")

            payload = self.build_notification_payload(secrets)
            return self.send_notifications(payload)

        except Exception as e:
            logger.error(f"Error during secrets check: {e}")
            return False

    def run(self) -> None:
        """Run the service based on configured mode."""
        if self.config.schedule.run_mode == "once":
            logger.info("Running in single-execution mode")
            success = self.run_check()
            sys.exit(0 if success else 1)
        else:
            logger.info(
                f"Running in scheduled mode with cron: {self.config.schedule.cron_schedule}"
            )
            self._run_scheduled()

    def _run_scheduled(self) -> None:
        """Run the service in scheduled mode."""
        cron = croniter(self.config.schedule.cron_schedule, datetime.now(timezone.utc))

        # Run immediately on startup
        logger.info("Running initial check on startup...")
        self.run_check()

        while True:
            next_run = cron.get_next(datetime)
            now = datetime.now(timezone.utc)

            # Handle timezone-naive datetime from croniter
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            sleep_seconds = (next_run - now).total_seconds()

            if sleep_seconds > 0:
                logger.info(f"Next check scheduled for {next_run.isoformat()}")
                time.sleep(sleep_seconds)

            logger.info("Running scheduled check...")
            self.run_check()


def main() -> None:
    """Main entry point."""
    try:
        logger.info("Entra ID Secrets Notification System starting...")
        config = load_config()

        # Set log level from config
        logging.getLogger().setLevel(config.log_level.upper())

        service = SecretsNotificationService(config)
        service.run()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
