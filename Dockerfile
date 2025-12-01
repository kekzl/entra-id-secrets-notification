# Entra ID Secrets Notification System
# Multi-stage build optimized for Python 3.12+

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pip and build tools
RUN pip install --no-cache-dir --upgrade pip

# Copy project files for installation
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .


# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser src/ ./src/

# Switch to non-root user
USER appuser

# Python runtime configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1

# Expose API port (configurable via API_PORT env var)
EXPOSE 8080

# Health check - verify the application can be imported
HEALTHCHECK --interval=5m --timeout=30s --start-period=10s --retries=3 \
    CMD python -c "from src.main import main; print('OK')" || exit 1

# Run the application using the installed entry point
ENTRYPOINT ["python", "-m", "src.main"]


# Development stage (optional)
FROM production AS development

USER root

# Install development dependencies
RUN pip install --no-cache-dir -e ".[dev]"

USER appuser

# Override entrypoint for development
ENTRYPOINT ["python", "-m", "pytest"]
