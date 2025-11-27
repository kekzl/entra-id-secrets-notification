"""Use case for checking and reporting expiring credentials."""

import logging
from dataclasses import dataclass

from ...domain.entities import ExpirationReport
from ...domain.services import ExpirationAnalyzer
from ...domain.value_objects import ExpirationThresholds
from ..ports import CredentialRepository, NotificationSender

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of the credential check use case."""

    report: ExpirationReport
    notifications_sent: int
    notifications_failed: int
    dry_run: bool

    @property
    def success(self) -> bool:
        """Check if the operation was successful."""
        return self.notifications_failed == 0


class CheckExpiringCredentials:
    """
    Use case for checking expiring credentials and sending notifications.

    This is the main application service that orchestrates the domain
    logic and infrastructure adapters.
    """

    def __init__(
        self,
        credential_repository: CredentialRepository,
        notification_senders: list[NotificationSender],
        thresholds: ExpirationThresholds,
        *,
        dry_run: bool = False,
    ) -> None:
        """
        Initialize the use case.

        Args:
            credential_repository: Adapter for retrieving credentials.
            notification_senders: List of notification adapters.
            thresholds: Expiration thresholds configuration.
            dry_run: If True, don't actually send notifications.
        """
        self._repository = credential_repository
        self._senders = [s for s in notification_senders if s.is_configured()]
        self._analyzer = ExpirationAnalyzer(thresholds)
        self._dry_run = dry_run

    async def execute(self) -> CheckResult:
        """
        Execute the credential check use case.

        Returns:
            CheckResult containing the report and notification status.
        """
        logger.info("Starting credential expiration check...")

        # Retrieve all credentials from the repository
        credentials = await self._repository.get_all_credentials()
        logger.info("Retrieved %d credentials", len(credentials))

        # Analyze credentials using domain service
        report = self._analyzer.analyze(credentials)
        logger.info("Analysis complete: %s", report.get_summary())

        # Send notifications if needed
        sent = 0
        failed = 0

        if not report.requires_notification:
            logger.info("No credentials require notification")
        elif self._dry_run:
            logger.info("DRY RUN: Would send notifications for %d credentials", len(report.credentials))
            self._log_dry_run_report(report)
        elif not self._senders:
            logger.warning("No notification senders configured")
        else:
            sent, failed = await self._send_notifications(report)

        return CheckResult(
            report=report,
            notifications_sent=sent,
            notifications_failed=failed,
            dry_run=self._dry_run,
        )

    async def _send_notifications(self, report: ExpirationReport) -> tuple[int, int]:
        """Send notifications through all configured senders."""
        sent = 0
        failed = 0

        for sender in self._senders:
            try:
                if await sender.send(report):
                    sent += 1
                    logger.info("Notification sent via %s", sender.__class__.__name__)
                else:
                    failed += 1
                    logger.warning("Notification failed via %s", sender.__class__.__name__)
            except Exception:
                failed += 1
                logger.exception("Error sending notification via %s", sender.__class__.__name__)

        return sent, failed

    def _log_dry_run_report(self, report: ExpirationReport) -> None:
        """Log report details in dry run mode."""
        logger.info("  Level: %s", report.notification_level.value)
        logger.info("  Summary: %s", report.get_summary())
        logger.info("  Applications affected: %d", report.affected_applications_count)
        logger.info("  Expired: %d", report.expired_count)
        logger.info("  Critical: %d", report.critical_count)
        logger.info("  Warning: %d", report.warning_count)
