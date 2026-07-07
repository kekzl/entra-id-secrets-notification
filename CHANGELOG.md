# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-07

### Added
- `Release` GitHub Actions workflow that builds and publishes the production
  Docker image to the GitHub Container Registry (GHCR) and creates a GitHub
  Release with auto-generated notes on every `v*.*.*` tag.
- This changelog.

### Changed
- Updated all runtime and development dependencies to their latest versions,
  including `fastapi` (0.139), `starlette` (1.3), `uvicorn` (0.50), `msal` (1.37),
  `croniter` (6.2), `pydantic` (2.13), `mypy` (2.1), `ruff` (0.15) and `pytest` (9.1).
- Raised the minimum version constraints in `pyproject.toml` to match the updated
  lockfile.
- Bumped the application version to `1.1.0`.

## [1.0.0] - 2026

### Added
- Initial release of the Entra ID Secrets Notification System.
- Monitoring of App Registration and Service Principal credentials for expiration.
- Notification channels: SMTP email, Microsoft Graph email, Microsoft Teams,
  Slack and generic webhook.
- Configurable critical / warning / info thresholds.
- Run-once and cron-based scheduling.
- Optional FastAPI REST API for health checks, reports and on-demand checks.
- Domain-Driven Design with a hexagonal (ports and adapters) architecture.
- Docker-based deployment.

[1.1.0]: https://github.com/kekzl/entra-id-secrets-notification/releases/tag/v1.1.0
[1.0.0]: https://github.com/kekzl/entra-id-secrets-notification/releases/tag/v1.0.0
