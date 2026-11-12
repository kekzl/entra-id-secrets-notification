"""Tests for ExpirationAnalyzer superseded-generation handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.entities import Credential
from src.domain.services import ExpirationAnalyzer
from src.domain.value_objects import (
    CredentialSource,
    CredentialType,
    ExpirationThresholds,
)

APP_ID = uuid4()
SP_OBJECT_ID = uuid4()
OTHER_SP_OBJECT_ID = uuid4()


def make_credential(
    *,
    display_name: str | None,
    days_from_now: int,
    credential_type: CredentialType = CredentialType.CERTIFICATE,
    source: CredentialSource = CredentialSource.SERVICE_PRINCIPAL,
    object_id: UUID | None = SP_OBJECT_ID,
    application_id: UUID = APP_ID,
) -> Credential:
    """Build a credential expiring `days_from_now` days from today."""
    return Credential(
        id=uuid4(),
        credential_type=credential_type,
        display_name=display_name,
        expiry_date=datetime.now(UTC) + timedelta(days=days_from_now),
        application_id=application_id,
        application_name="P2P Server",
        source=source,
        object_id=object_id,
    )


class TestSupersededGenerations:
    """Expired credentials replaced by a newer generation must not alert."""

    def test_superseded_expired_generation_is_excluded(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """The MS-Organization-P2P-Access [2025]/[2026] rollover case."""
        old = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2025]", days_from_now=-10
        )
        new = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2026]", days_from_now=300
        )

        analyzer = ExpirationAnalyzer(default_thresholds)
        report = analyzer.analyze([old, new])

        assert report.expired_count == 0
        assert old.id not in [c.id for c in report.credentials]
        assert analyzer.filter_requiring_attention([old, new]) == []

    def test_expired_without_successor_is_reported(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """An expired credential with no replacement still alerts."""
        old = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2025]", days_from_now=-10
        )

        report = ExpirationAnalyzer(default_thresholds).analyze([old])

        assert report.expired_count == 1
        assert report.credentials[0].id == old.id

    def test_expired_successor_does_not_suppress(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """If the newer generation has also expired, both are reported."""
        older = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2024]", days_from_now=-400
        )
        old = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2025]", days_from_now=-10
        )

        report = ExpirationAnalyzer(default_thresholds).analyze([older, old])

        assert report.expired_count == 2

    def test_same_name_on_other_owner_does_not_suppress(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """A healthy credential on a different service principal is unrelated."""
        old = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2025]", days_from_now=-10
        )
        new_elsewhere = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2026]",
            days_from_now=300,
            object_id=OTHER_SP_OBJECT_ID,
        )

        report = ExpirationAnalyzer(default_thresholds).analyze([old, new_elsewhere])

        assert report.expired_count == 1

    def test_unnamed_credentials_are_never_suppressed(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """Credentials without a display name cannot be grouped into a family."""
        expired_secret = make_credential(
            display_name=None,
            days_from_now=-3,
            credential_type=CredentialType.PASSWORD,
            source=CredentialSource.APP_REGISTRATION,
            object_id=None,
        )
        healthy_secret = make_credential(
            display_name=None,
            days_from_now=200,
            credential_type=CredentialType.PASSWORD,
            source=CredentialSource.APP_REGISTRATION,
            object_id=None,
        )

        report = ExpirationAnalyzer(default_thresholds).analyze([expired_secret, healthy_secret])

        assert report.expired_count == 1

    def test_unrelated_healthy_credential_does_not_suppress(
        self, default_thresholds: ExpirationThresholds
    ) -> None:
        """A different name or type on the same owner is not a successor."""
        old = make_credential(
            display_name="CN=MS-Organization-P2P-Access [2025]", days_from_now=-10
        )
        unrelated = make_credential(
            display_name="some-other-secret",
            days_from_now=200,
            credential_type=CredentialType.PASSWORD,
        )

        report = ExpirationAnalyzer(default_thresholds).analyze([old, unrelated])

        assert report.expired_count == 1
