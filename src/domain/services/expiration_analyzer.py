"""Domain service for analyzing credential expirations."""

from ..entities import Credential, ExpirationReport
from ..value_objects import ExpirationThresholds


class ExpirationAnalyzer:
    """Domain service for analyzing credential expirations."""

    def __init__(self, thresholds: ExpirationThresholds) -> None:
        """Initialize analyzer with thresholds."""
        self._thresholds = thresholds

    def analyze(self, credentials: list[Credential]) -> ExpirationReport:
        """
        Analyze credentials and generate an expiration report.

        Args:
            credentials: List of credentials to analyze.

        Returns:
            ExpirationReport with categorized credentials.
        """
        # Filter to only credentials within the info threshold
        relevant = [
            c for c in credentials
            if c.requires_notification(self._thresholds)
        ]

        return ExpirationReport(
            credentials=relevant,
            thresholds=self._thresholds,
        )

    def filter_requiring_attention(
        self, credentials: list[Credential]
    ) -> list[Credential]:
        """Filter credentials that require immediate attention."""
        return [
            c for c in credentials
            if c.get_status(self._thresholds).requires_attention
        ]
