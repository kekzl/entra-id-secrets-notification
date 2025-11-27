# Entra ID Secrets Notification System

A Docker-based service that monitors Microsoft Entra ID (Azure AD) application secrets and certificates for expiration and sends notifications through multiple channels.

## Features

- **Automatic Monitoring**: Scans all app registrations in your Entra ID tenant for expiring secrets and certificates
- **Multiple Notification Channels**:
  - Email (SMTP)
  - Microsoft Teams (Incoming Webhook)
  - Slack (Incoming Webhook)
  - Generic HTTP Webhook (JSON payload)
- **Configurable Thresholds**: Set custom warning levels for critical, warning, and info notifications
- **Flexible Scheduling**: Run once or on a cron schedule
- **Docker-Ready**: Easy deployment with Docker and Docker Compose
- **Secure**: Runs as non-root user with minimal permissions

## Prerequisites

1. **Microsoft Entra ID App Registration** with the following:
   - API Permission: `Microsoft Graph > Application.Read.All` (Application permission)
   - Admin consent granted for the permission
   - Client secret created

2. **Docker** and **Docker Compose** installed

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd entra-id-secrets-notification
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and configure:
- Azure credentials (required)
- At least one notification channel
- Threshold and schedule settings

### 3. Run with Docker Compose

```bash
# Build and run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### 4. Run Once (Manual Check)

```bash
# Set RUN_MODE=once in .env, then:
docker-compose up
```

## Configuration

### Azure/Entra ID Settings

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_TENANT_ID` | Your Entra ID tenant ID | Yes |
| `AZURE_CLIENT_ID` | App registration client ID | Yes |
| `AZURE_CLIENT_SECRET` | App registration client secret | Yes |

### Notification Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `CRITICAL_THRESHOLD_DAYS` | 7 | Days until expiry for critical alerts |
| `WARNING_THRESHOLD_DAYS` | 30 | Days until expiry for warning alerts |
| `INFO_THRESHOLD_DAYS` | 90 | Days until expiry for info alerts |

### Schedule Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_MODE` | scheduled | `once` or `scheduled` |
| `CRON_SCHEDULE` | `0 8 * * *` | Cron expression (daily at 8 AM UTC) |
| `LOG_LEVEL` | INFO | DEBUG, INFO, WARNING, ERROR |
| `DRY_RUN` | false | Test mode without sending notifications |

### Email (SMTP) Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_ENABLED` | false | Enable email notifications |
| `SMTP_SERVER` | - | SMTP server hostname |
| `SMTP_PORT` | 587 | SMTP port |
| `SMTP_USERNAME` | - | SMTP username |
| `SMTP_PASSWORD` | - | SMTP password |
| `SMTP_FROM` | - | From email address |
| `SMTP_TO` | - | To addresses (comma-separated) |
| `SMTP_USE_TLS` | true | Use TLS encryption |

### Microsoft Teams Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAMS_ENABLED` | false | Enable Teams notifications |
| `TEAMS_WEBHOOK_URL` | - | Incoming webhook URL |

### Slack Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_ENABLED` | false | Enable Slack notifications |
| `SLACK_WEBHOOK_URL` | - | Incoming webhook URL |

### Generic Webhook

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_ENABLED` | false | Enable webhook notifications |
| `WEBHOOK_URL` | - | HTTP endpoint URL |

## Setting Up Entra ID App Registration

1. Go to [Azure Portal](https://portal.azure.com) > **Microsoft Entra ID** > **App registrations**

2. Click **New registration**:
   - Name: `Entra ID Secrets Monitor`
   - Supported account types: Single tenant
   - Click **Register**

3. Note the **Application (client) ID** and **Directory (tenant) ID**

4. Go to **Certificates & secrets** > **Client secrets** > **New client secret**:
   - Add a description
   - Set expiration
   - Click **Add**
   - Copy the **Value** immediately

5. Go to **API permissions** > **Add a permission**:
   - Select **Microsoft Graph**
   - Select **Application permissions**
   - Search for and add `Application.Read.All`
   - Click **Add permissions**

6. Click **Grant admin consent** (requires admin privileges)

## Setting Up Notification Channels

### Microsoft Teams

1. In Teams, go to the channel where you want notifications
2. Click `•••` > **Connectors** > **Incoming Webhook**
3. Configure the webhook name and icon
4. Copy the webhook URL to `TEAMS_WEBHOOK_URL`

### Slack

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or select existing
3. Go to **Incoming Webhooks** > Enable
4. Add a new webhook to your workspace
5. Copy the webhook URL to `SLACK_WEBHOOK_URL`

## Webhook JSON Payload

For generic webhook integrations, the service sends this JSON structure:

```json
{
  "event_type": "entra_id_secrets_alert",
  "timestamp": "2024-01-15T08:00:00+00:00",
  "level": "critical",
  "title": "Entra ID Secrets Expiration Alert",
  "summary": "5 secrets/certificates requiring attention: 1 expired, 2 critical, 2 warning",
  "statistics": {
    "total_apps_affected": 3,
    "expired_count": 1,
    "critical_count": 2,
    "warning_count": 2,
    "info_count": 0
  },
  "secrets": [
    {
      "app_id": "app-guid",
      "app_name": "My Application",
      "secret_id": "secret-guid",
      "secret_type": "password",
      "display_name": "API Key",
      "expiry_date": "2024-01-20T00:00:00+00:00",
      "days_until_expiry": 5,
      "is_expired": false
    }
  ]
}
```

## Development

### Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_TENANT_ID=...
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export DRY_RUN=true

# Run
python -m src.main
```

### Building Docker Image

```bash
docker build -t entra-id-secrets-notification .
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET`
   - Ensure the client secret hasn't expired
   - Check that admin consent was granted

2. **No Notifications Sent**
   - Enable at least one notification channel
   - Check `DRY_RUN` is set to `false`
   - Verify webhook URLs are correct
   - Check container logs for errors

3. **Permission Denied Errors**
   - Ensure `Application.Read.All` permission is granted
   - Verify admin consent was given

### Viewing Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f entra-id-secrets-notification
```

## License

MIT License - see [LICENSE](LICENSE) file for details.
