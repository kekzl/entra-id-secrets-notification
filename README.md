# Entra ID Secrets Notification System

A Docker-based service that monitors Microsoft Entra ID (Azure AD) application secrets and certificates for expiration and sends notifications through multiple channels.

Built using **Domain-Driven Design (DDD)** and **Hexagonal Architecture** (Ports and Adapters) patterns, following Python 2025 best practices.

## Features

- **Automatic Monitoring**: Scans all app registrations in your Entra ID tenant
- **Multiple Notification Channels**: Email (SMTP), Microsoft Graph Email, Microsoft Teams, Slack, Generic Webhook
- **Configurable Thresholds**: Critical, Warning, and Info levels
- **Flexible Scheduling**: Run once or on a cron schedule
- **REST API**: Optional API for health checks, reports, and on-demand checks (no credential details exposed)
- **Clean Architecture**: DDD with hexagonal architecture for maintainability
- **Type Safety**: Full type hints with Python 3.12+ features
- **Async/Await**: Non-blocking I/O for better performance
- **Docker-Ready**: Production-ready containerization

## Architecture

This project follows **Hexagonal Architecture** (Ports and Adapters) with **Domain-Driven Design** principles:

```
src/
├── domain/                    # Core business logic (no external dependencies)
│   ├── entities/              # Domain entities with identity
│   │   ├── credential.py      # Credential entity
│   │   ├── application.py     # Application entity
│   │   └── expiration_report.py  # Aggregate root
│   ├── value_objects/         # Immutable value objects
│   │   ├── credential_type.py
│   │   ├── expiration_status.py
│   │   ├── notification_level.py
│   │   └── thresholds.py
│   ├── services/              # Domain services
│   │   └── expiration_analyzer.py
│   └── exceptions.py          # Domain exceptions
│
├── application/               # Application layer (use cases)
│   ├── ports/                 # Interfaces (driven/secondary ports)
│   │   ├── credential_repository.py  # Port for data retrieval
│   │   └── notification_sender.py    # Port for notifications
│   ├── use_cases/             # Application services
│   │   └── check_expiring_credentials.py
│   └── exceptions.py          # Application exceptions
│
├── infrastructure/            # Infrastructure layer (adapters)
│   ├── adapters/
│   │   ├── api/               # REST API adapter (FastAPI)
│   │   │   ├── app.py
│   │   │   └── models.py
│   │   ├── entra_id/          # Entra ID adapter (implements CredentialRepository)
│   │   │   ├── graph_client.py
│   │   │   └── repository.py
│   │   └── notifications/     # Notification adapters (implement NotificationSender)
│   │       ├── email.py       # SMTP email
│   │       ├── graph_email.py # Microsoft Graph API email
│   │       ├── teams.py
│   │       ├── slack.py
│   │       └── webhook.py
│   └── config/                # Configuration loading
│       └── settings.py
│
└── main.py                    # Composition root (dependency injection)
```

### Key Concepts

- **Domain Layer**: Pure business logic with no external dependencies. Contains entities, value objects, and domain services.
- **Application Layer**: Orchestrates use cases using domain objects. Defines ports (interfaces) for external systems.
- **Infrastructure Layer**: Implements adapters that fulfill the ports. Contains all external system integrations.
- **Composition Root**: Wires everything together using dependency injection.

## Prerequisites

1. **Microsoft Entra ID App Registration** with:
   - API Permission: `Microsoft Graph > Application.Read.All` (Application)
   - API Permission: `Microsoft Graph > Mail.Send` (Application) - only if using Graph Email
   - Admin consent granted
   - Client secret created

2. **Python 3.12+** (for local development)

3. **Docker** and **Docker Compose** (for containerized deployment)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd entra-id-secrets-notification
cp .env.example .env
# Edit .env with your Azure credentials and notification settings
```

### 2. Run with Docker Compose

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### 3. Run Once (Manual Check)

```bash
# Set RUN_MODE=once in .env, then:
docker compose up
```

## Configuration

### Required: Azure/Entra ID

| Variable | Description |
|----------|-------------|
| `AZURE_TENANT_ID` | Your Entra ID tenant ID |
| `AZURE_CLIENT_ID` | App registration client ID |
| `AZURE_CLIENT_SECRET` | App registration client secret |

### Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `CRITICAL_THRESHOLD_DAYS` | 7 | Days for critical alerts |
| `WARNING_THRESHOLD_DAYS` | 30 | Days for warning alerts |
| `INFO_THRESHOLD_DAYS` | 90 | Days for info alerts |

### Schedule

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_MODE` | scheduled | `once` or `scheduled` |
| `CRON_SCHEDULE` | `0 8 * * *` | Cron expression |
| `LOG_LEVEL` | INFO | DEBUG, INFO, WARNING, ERROR |
| `DRY_RUN` | false | Test mode (no notifications) |

### Notification Channels

#### Email (SMTP)
```env
SMTP_ENABLED=true
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user
SMTP_PASSWORD=pass
SMTP_FROM=noreply@example.com
SMTP_TO=admin@example.com
SMTP_USE_TLS=true
```

#### Microsoft Teams
```env
TEAMS_ENABLED=true
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
```

#### Slack
```env
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

#### Generic Webhook
```env
WEBHOOK_ENABLED=true
WEBHOOK_URL=https://your-endpoint.com/notify
```

#### Microsoft Graph Email
Send email via Microsoft Graph API. Useful when SMTP is not available or you want to use Microsoft 365 mailboxes.

> **Note**: Requires `Mail.Send` application permission with admin consent. If Graph-specific credentials are not set, it uses the main Azure credentials.

```env
GRAPH_EMAIL_ENABLED=true
GRAPH_EMAIL_FROM=notifications@yourdomain.com
GRAPH_EMAIL_TO=admin@example.com,security@example.com
# Optional: Use different credentials than the main app
GRAPH_EMAIL_TENANT_ID=
GRAPH_EMAIL_CLIENT_ID=
GRAPH_EMAIL_CLIENT_SECRET=
# Save sent emails to Sent Items folder
GRAPH_EMAIL_SAVE_TO_SENT=false
```

### REST API (Optional)

Enable the REST API for health checks, summary reports, and on-demand credential checks.

> **Security Note**: The API does NOT expose credential details - only statistics and summaries.

```env
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8080
```

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check - returns service status |
| `GET` | `/api/v1/report` | Get latest report summary (no credential details) |
| `POST` | `/api/v1/check` | Trigger on-demand credential check |

#### Example: Health Check
```bash
curl http://localhost:8080/health
```
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-15T08:00:00Z"
}
```

#### Example: Get Report
```bash
curl http://localhost:8080/api/v1/report
```
```json
{
  "generated_at": "2025-01-15T08:00:00Z",
  "notification_level": "warning",
  "summary": "5 credentials requiring attention: 1 expired, 2 critical, 2 warning",
  "statistics": {
    "total_applications": 3,
    "total_credentials": 5,
    "expired_count": 1,
    "critical_count": 2,
    "warning_count": 2,
    "healthy_count": 0
  },
  "thresholds": {
    "critical_days": 7,
    "warning_days": 30,
    "info_days": 90
  },
  "requires_notification": true
}
```

#### Example: Trigger Check
```bash
curl -X POST http://localhost:8080/api/v1/check
```

#### OpenAPI Documentation

When API is enabled, interactive documentation is available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Webhook JSON Payload

For generic webhook integrations:

```json
{
  "event_type": "entra_id_secrets_alert",
  "timestamp": "2025-01-15T08:00:00+00:00",
  "level": "critical",
  "summary": "5 credentials requiring attention: 1 expired, 2 critical, 2 warning",
  "statistics": {
    "total_applications_affected": 3,
    "total_credentials": 5,
    "expired_count": 1,
    "critical_count": 2,
    "warning_count": 2,
    "healthy_count": 0
  },
  "credentials": [
    {
      "application_id": "app-guid",
      "application_name": "My Application",
      "credential_id": "credential-guid",
      "credential_type": "password",
      "display_name": "API Key",
      "expiry_date": "2025-01-20T00:00:00+00:00",
      "days_until_expiry": 5,
      "is_expired": false,
      "status": "critical"
    }
  ]
}
```

## Setting Up Entra ID

1. Go to [Azure Portal](https://portal.azure.com) > **Microsoft Entra ID** > **App registrations**

2. Click **New registration**:
   - Name: `Entra ID Secrets Monitor`
   - Account types: Single tenant
   - Click **Register**

3. Note the **Application (client) ID** and **Directory (tenant) ID**

4. **Certificates & secrets** > **Client secrets** > **New client secret**

5. **API permissions** > **Add a permission**:
   - Microsoft Graph > Application permissions
   - Add `Application.Read.All` (required for monitoring)
   - Add `Mail.Send` (only if using Microsoft Graph Email notifications)
   - Click **Grant admin consent**

## Troubleshooting

### Authentication Errors
- Verify Azure credentials
- Check client secret hasn't expired
- Confirm admin consent was granted

### No Notifications
- Enable at least one notification channel
- Check `DRY_RUN=false`
- Verify webhook URLs

### Permission Errors
- Ensure `Application.Read.All` permission
- Verify admin consent

### View Logs
```bash
docker compose logs -f
```

## License

MIT License - see [LICENSE](LICENSE) file.
