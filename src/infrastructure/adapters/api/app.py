"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from ....domain.entities import ExpirationReport
from .models import (
    CheckResponse,
    ErrorResponse,
    HealthResponse,
    ReportResponse,
    StatisticsResponse,
    ThresholdsResponse,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Coroutine

    from ....application.use_cases.check_expiring_credentials import CheckResult

logger = logging.getLogger(__name__)


def _report_to_response(report: ExpirationReport) -> ReportResponse:
    """Convert domain report to API response (no credential details)."""
    return ReportResponse(
        generated_at=report.generated_at,
        notification_level=report.notification_level.value,
        summary=report.get_summary(),
        statistics=StatisticsResponse(
            total_applications=report.affected_applications_count,
            total_credentials=report.total_count,
            expired_count=report.expired_count,
            critical_count=report.critical_count,
            warning_count=report.warning_count,
            healthy_count=report.healthy_count,
        ),
        thresholds=ThresholdsResponse(
            critical_days=report.thresholds.critical,
            warning_days=report.thresholds.warning,
            info_days=report.thresholds.info,
        ),
        requires_notification=report.requires_notification,
    )


class ApiState:
    """Shared state for API endpoints."""

    def __init__(
        self,
        check_func: Callable[[], Coroutine[None, None, CheckResult]],
        version: str = "1.0.0",
    ) -> None:
        """Initialize API state."""
        self.check_func = check_func
        self.version = version
        self.last_report: ExpirationReport | None = None
        self.last_check_at: datetime | None = None


def create_app(
    check_func: Callable[[], Coroutine[None, None, CheckResult]],
    version: str = "1.0.0",
) -> FastAPI:
    """
    Create FastAPI application.

    Args:
        check_func: Async function to execute credential check.
        version: Application version string.

    Returns:
        Configured FastAPI application.
    """
    state = ApiState(check_func=check_func, version=version)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan handler."""
        logger.info("API server starting...")
        yield
        logger.info("API server shutting down...")

    app = FastAPI(
        title="Entra ID Secrets Notification API",
        description="Monitor Entra ID application secrets and certificates for expiration. "
        "This API provides health checks, summary reports, and on-demand credential checks. "
        "**No credential details are exposed through this API.**",
        version=version,
        lifespan=lifespan,
        responses={
            500: {"model": ErrorResponse, "description": "Internal server error"},
        },
    )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Health check",
        description="Check if the service is healthy and running.",
    )
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy",
            version=state.version,
            timestamp=datetime.now(UTC),
        )

    @app.get(
        "/api/v1/report",
        response_model=ReportResponse,
        tags=["Reports"],
        summary="Get latest report",
        description="Get the latest credential expiration report summary. "
        "Does not include any credential details for security.",
        responses={
            404: {"model": ErrorResponse, "description": "No report available"},
        },
    )
    async def get_report() -> ReportResponse:
        if state.last_report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No report available. Trigger a check first using POST /api/v1/check",
            )
        return _report_to_response(state.last_report)

    @app.post(
        "/api/v1/check",
        response_model=CheckResponse,
        tags=["Operations"],
        summary="Trigger credential check",
        description="Trigger an on-demand credential expiration check. "
        "This will scan all Entra ID applications and optionally send notifications.",
        responses={
            500: {"model": ErrorResponse, "description": "Check failed"},
        },
    )
    async def trigger_check() -> CheckResponse:
        try:
            logger.info("API: Triggering credential check...")
            result = await state.check_func()

            # Store the report for future queries
            state.last_report = result.report
            state.last_check_at = datetime.now(UTC)

            return CheckResponse(
                success=result.success,
                message="Check completed successfully" if result.success else "Check completed with errors",
                report=_report_to_response(result.report),
                notifications_sent=result.notifications_sent,
                notifications_failed=result.notifications_failed,
                dry_run=result.dry_run,
            )

        except Exception as e:
            logger.exception("API: Credential check failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Credential check failed: {e}",
            ) from e

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        """Handle uncaught exceptions."""
        logger.exception("Unhandled exception in API")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    return app
