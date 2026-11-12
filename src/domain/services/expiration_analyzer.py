"""Domain service for analyzing credential expirations."""

import re
from uuid import UUID

from ..entities import Credential, ExpirationReport
from ..value_objects import ExpirationThresholds

# Matches a trailing bracketed generation tag such as " [2025]" in
# "CN=MS-Organization-P2P-Access [2025]".
_TRAILING_TAG = re.compile(r"\s*\[[^\]]*\]\s*$")


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
        # Drop expired credentials that have already been replaced by a
        # newer, still-valid generation of the same credential.
        active = self._exclude_superseded(credentials)

        # Filter to only credentials within the info threshold
        relevant = [c for c in active if c.requires_notification(self._thresholds)]

        return ExpirationReport(
            credentials=relevant,
            thresholds=self._thresholds,
        )

    def filter_requiring_attention(self, credentials: list[Credential]) -> list[Credential]:
        """Filter credentials that require immediate attention."""
        active = self._exclude_superseded(credentials)
        return [c for c in active if c.get_status(self._thresholds).requires_attention]

    @staticmethod
    def _family_key(credential: Credential) -> tuple[str, UUID, str, str]:
        """
        Group key identifying one logical credential across generations.

        Credentials whose display names differ only in a trailing bracketed
        tag (e.g. "CN=MS-Organization-P2P-Access [2025]" vs "... [2026]")
        belong to the same family. Credentials without a usable display
        name form a family of one and are never treated as superseded.
        """
        owner = credential.object_id or credential.application_id
        base = _TRAILING_TAG.sub("", (credential.display_name or "").strip()).strip()
        if not base:
            base = f"__unnamed__{credential.id}"
        return (
            credential.source.value,
            owner,
            credential.credential_type.value,
            base.casefold(),
        )

    def _exclude_superseded(self, credentials: list[Credential]) -> list[Credential]:
        """
        Remove expired credentials that already have a valid successor.

        A credential counts as superseded when another credential in the
        same family (same owner, type and display-name base) expires later
        and has not itself expired. This mirrors managed rollover schemes
        such as Microsoft's MS-Organization-P2P-Access certificates, where
        the retired generation stays listed next to its replacement and
        would otherwise alert forever even though nothing is wrong.
        """
        families: dict[tuple[str, UUID, str, str], list[Credential]] = {}
        for credential in credentials:
            families.setdefault(self._family_key(credential), []).append(credential)

        result: list[Credential] = []
        for credential in credentials:
            if credential.is_expired:
                siblings = families[self._family_key(credential)]
                has_valid_successor = any(
                    sibling.id != credential.id
                    and not sibling.is_expired
                    and sibling.expiry_date > credential.expiry_date
                    for sibling in siblings
                )
                if has_valid_successor:
                    continue
            result.append(credential)
        return result
