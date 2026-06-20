# Enterprise Features

In a Cloud Gateway includes enterprise-grade load balancing, health monitoring, SMTP notifications, and alerting.

## Load Balancing

Create **Backend Pools** under `/backend-pools` or link a pool to a proxy route.

Supported methods:

- Round Robin
- Least Connections
- IP Hash
- Random
- Weighted Round Robin

NGINX `upstream {}` blocks are generated automatically with optional `backup` servers for failover.

## Health Monitoring

Background checks run every 60 seconds (configurable via `HEALTH_CHECK_INTERVAL_SECONDS`).

Check types: TCP, HTTP, HTTPS, custom health endpoint.

View status and uptime graphs at `/health`.

## SMTP Notifications

Configure SMTP at `/settings` (admin only). Passwords are encrypted at rest with Fernet (derived from `ENCRYPTION_KEY` or `SECRET_KEY`).

Supported encryption modes:

- **None** — plain SMTP (no TLS)
- **STARTTLS** — upgrade connection with TLS after connect (typical port 587)
- **SSL / SMTPS** — implicit TLS from connect (typical port 465)

## Notification Types

- Backend offline / restored
- SSL certificate expiring / renewed
- Proxy host created / modified / deleted
- NGINX validation or reload failures
- System resource thresholds
- Login security events

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENCRYPTION_KEY` | derived from `SECRET_KEY` | Fernet key material |
| `SCHEDULER_ENABLED` | `true` | Background jobs |
| `ALEMBIC_UPGRADE` | `true` | Run migrations on startup |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `60` | Health job interval |
| `SYSTEM_MONITOR_INTERVAL_SECONDS` | `300` | CPU/RAM/disk checks |
| `SSL_ALERT_INTERVAL_SECONDS` | `86400` | Certificate expiry scan |
| `HEALTH_WARNING_MS` | `2000` | Slow response warning threshold |

## API Endpoints

- `/api/backend-pools`
- `/api/backend-servers`
- `/api/load-balancers`
- `/api/health-checks`
- `/api/smtp`
- `/api/notifications`
- `/api/system-alerts`
