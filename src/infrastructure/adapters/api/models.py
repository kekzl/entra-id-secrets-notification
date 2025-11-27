"""API response models (no credential details exposed)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"]
    version: str
    timestamp: datetime


class ThresholdsResponse(BaseModel):
    """Configured thresholds."""

    critical_days: int
    warning_days: int
    info_days: int


class StatisticsResponse(BaseModel):
    """Credential statistics (no details)."""

    total_applications: int = Field(description="Total applications scanned")
    total_credentials: int = Field(description="Total credentials found")
    expired_count: int = Field(description="Number of expired credentials")
    critical_count: int = Field(description="Credentials expiring within critical threshold")
    warning_count: int = Field(description="Credentials expiring within warning threshold")
    healthy_count: int = Field(description="Healthy credentials")


class ReportResponse(BaseModel):
    """Expiration report summary (no credential details)."""

    generated_at: datetime
    notification_level: str = Field(description="Overall severity: critical, warning, or info")
    summary: str = Field(description="Human-readable summary")
    statistics: StatisticsResponse
    thresholds: ThresholdsResponse
    requires_notification: bool


class CheckResponse(BaseModel):
    """Response from triggering a check."""

    success: bool
    message: str
    report: ReportResponse | None = None
    notifications_sent: int = 0
    notifications_failed: int = 0
    dry_run: bool = False


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
