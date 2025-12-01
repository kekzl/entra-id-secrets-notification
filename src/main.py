#!/usr/bin/env python3
"""
Entra ID Secrets Notification System

Composition root and application entry point.
Wires together all layers following hexagonal architecture principles.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from croniter import croniter

from .application.use_cases import CheckExpiringCredentials
from .infrastructure.adapters import (
    EmailNotificationSender,
    EntraIdCredentialRepository,
    GraphEmailNotificationSender,
    SlackNotificationSender,
    TeamsNotificationSender,
    WebhookNotificationSender,
)
from .infrastructure.config import Settings, load_settings

if TYPE_CHECKING:
    from .application.ports import NotificationSender
    from .application.use_cases.check_expiring_credentials import CheckResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Application version
__version__ = "1.0.0"


class ApplicationContainer:
    """
    Dependency injection container.

    Responsible for creating and wiring all application components.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize container with settings."""
        self._settings = settings

    def create_credential_repository(self) -> EntraIdCredentialRepository:
        """Create the credential repository adapter."""
        return EntraIdCredentialRepository(
            self._settings.graph_config,
            monitor_service_principals=self._settings.monitor_service_principals,
        )

    def create_notification_senders(self) -> list[NotificationSender]:
        """Create all configured notification sender adapters."""
        senders: list[NotificationSender] = [
            EmailNotificationSender(self._settings.email_config),
            GraphEmailNotificationSender(self._settings.graph_email_config),
            TeamsNotificationSender(self._settings.teams_config),
            SlackNotificationSender(self._settings.slack_config),
            WebhookNotificationSender(self._settings.webhook_config),
        ]

        configured = [s for s in senders if s.is_configured()]
        logger.info(
            "Configured notification senders: %s",
            [s.__class__.__name__ for s in configured] or "None",
        )

        return senders

    def create_check_use_case(self) -> CheckExpiringCredentials:
        """Create the main use case with all dependencies."""
        return CheckExpiringCredentials(
            credential_repository=self.create_credential_repository(),
            notification_senders=self.create_notification_senders(),
            thresholds=self._settings.thresholds,
            dry_run=self._settings.dry_run,
        )


class Application:
    """
    Main application orchestrator.

    Handles run modes (single execution, scheduled, or API) and lifecycle.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize application with settings."""
        self._settings = settings
        self._container = ApplicationContainer(settings)

    async def run_once(self) -> CheckResult:
        """Execute a single credential check."""
        use_case = self._container.create_check_use_case()
        return await use_case.execute()

    async def run_scheduled(self) -> None:
        """Run in scheduled mode with cron expression."""
        logger.info("Starting scheduled mode with cron: %s", self._settings.cron_schedule)

        # Run immediately on startup
        logger.info("Running initial check on startup...")
        await self.run_once()

        cron = croniter(self._settings.cron_schedule, datetime.now(UTC))

        while True:
            next_run = cron.get_next(datetime)
            now = datetime.now(UTC)

            # Handle timezone-naive datetime from croniter
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=UTC)

            sleep_seconds = (next_run - now).total_seconds()

            if sleep_seconds > 0:
                logger.info("Next check scheduled for %s", next_run.isoformat())
                await asyncio.sleep(sleep_seconds)

            logger.info("Running scheduled check...")
            await self.run_once()

    def run_api(self) -> None:
        """Run in API server mode."""
        import uvicorn

        from .infrastructure.adapters.api import create_app

        logger.info(
            "Starting API server on %s:%d",
            self._settings.api_host,
            self._settings.api_port,
        )

        # Create FastAPI app with check function
        app = create_app(
            check_func=self.run_once,
            version=__version__,
        )

        # Run uvicorn server
        uvicorn.run(
            app,
            host=self._settings.api_host,
            port=self._settings.api_port,
            log_level=self._settings.log_level.lower(),
        )

    async def run(self) -> int:
        """
        Run the application based on configured mode.

        Returns:
            Exit code (0 for success, 1 for failure).
        """
        # API mode takes precedence if enabled
        if self._settings.api_enabled:
            self.run_api()
            return 0

        match self._settings.run_mode.lower():
            case "once":
                logger.info("Running in single-execution mode")
                result = await self.run_once()
                return 0 if result.success else 1

            case "scheduled":
                await self.run_scheduled()
                return 0  # Never reached in scheduled mode

            case _:
                logger.error(
                    "Invalid RUN_MODE: %s (use 'once', 'scheduled', or set API_ENABLED=true)",
                    self._settings.run_mode,
                )
                return 1


async def async_main() -> int:
    """Async entry point."""
    try:
        logger.info("Entra ID Secrets Notification System starting...")

        settings = load_settings()
        logging.getLogger().setLevel(settings.log_level.upper())

        app = Application(settings)
        return await app.run()

    except ValueError as e:
        logger.error("Configuration error: %s", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        return 0
    except Exception:
        logger.exception("Unexpected error")
        return 1


def main() -> None:
    """Main entry point."""
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
