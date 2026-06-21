# In a Cloud Gateway

Production-ready web administration tool for managing Nginx reverse proxy configurations, Let's Encrypt certificates, and operational tasks on Ubuntu 24.04.

## Documentation

- **[Proxy Setup Manual](docs/PROXY_SETUP_MANUAL.md)** — complete guide to creating proxies in the Admin UI, traffic flow, HTTPS, and troubleshooting
- **[Application Catalog](docs/APPLICATION_CATALOG.md)** — YAML template schema, API, wizard flow, and contributor guide

## Features

- Manage reverse proxy apps (create, edit, delete, enable/disable)
- **Application Catalog** with 100+ YAML-backed templates, group browsing, search/filters, and a 7-step setup wizard
- **Enterprise load balancing** with backend pools, weighted servers, and active/passive failover
- **Backend health monitoring** with TCP/HTTP/HTTPS checks, uptime history, and dashboard widgets
- **SMTP notifications** with encrypted credentials and configurable alert recipients
- **Scheduled alerts** for SSL expiry, system resources (CPU/RAM/disk), and NGINX failures
- Safe config workflow: backup before write, `nginx -t` before reload, automatic rollback on failure
- Certificate management via Certbot
- Error/access log viewer with domain filter
- **Enterprise observability**: metrics dashboard, traffic/status-code analytics, live & failed request views, metric alert rules, retention settings
- Session authentication with Argon2, CSRF protection, login rate limiting, IP allowlist
- Audit log for all mutating actions

See [Enterprise Features](docs/ENTERPRISE_FEATURES.md) for load balancing, health checks, SMTP, and alerting details.

See [Observability](docs/OBSERVABILITY.md) for metrics collection, stub_status, enhanced logging, retention, and alert rules.

See [Roadmap](docs/ROADMAP.md) for V1–V4 feature status.

## Architecture

- Backend: FastAPI on `127.0.0.1:8080`
- Frontend: React + TypeScript + Tailwind (served by backend in production)
- Database: SQLite in `/var/lib/reverse-proxy-admin/app.db`
- Backups: `/var/lib/reverse-proxy-admin/backups/`

## Requirements

- Ubuntu 24.04
- Nginx installed and running
- Certbot with nginx plugin
- Python 3.12+
- Node.js 20+ (build only)

## Quick install from GitHub (Ubuntu 24.04)

On a fresh Linux server with `git` and `sudo`:

```bash
git clone https://github.com/Cloud-Man42/reverse-proxy-admin.git
cd reverse-proxy-admin
sudo bash deploy/install-from-repo.sh
```

This runs `deploy/install-prerequisites.sh` first. That script is **idempotent** and only installs missing packages such as Nginx, Certbot, Python venv tooling, Node.js, `htpasswd`, OpenSSL, and UFW.

After install, log in with the administrator credentials from `deploy/env.example` and change the password under **Admin UI → Users** before production use.

Adjust network settings if needed:

```bash
sudo nano /etc/nginx-admin/env
sudo systemctl restart nginx-admin
```

Install only OS prerequisites (without deploying the app):

```bash
sudo bash deploy/install-prerequisites.sh
```

## Docker install (recommended for new deployments)

Runs Nginx, Certbot, and the admin API in one container with persistent volumes for configs, certificates, and data.

Requirements on the host: Docker Engine + Docker Compose plugin.

```bash
git clone https://github.com/Cloud-Man42/reverse-proxy-admin.git
cd reverse-proxy-admin
bash deploy/docker/install-docker.sh
```

Or manually:

```bash
cp deploy/docker/env.docker.example .env
# edit .env — set SECRET_KEY, CERTBOT_EMAIL, SERVER_PUBLIC_IP
docker compose up -d --build
```

| Port | Purpose |
|------|---------|
| 80 | HTTP reverse proxy + ACME challenges |
| 443 | HTTPS reverse proxy |
| 8443 | Admin UI (HTTPS, internal use) |

Log in with the credentials in `.env` and change the password under **Users** immediately.

Useful commands:

```bash
docker compose logs -f reverse-proxy
docker compose restart reverse-proxy
docker compose down
```

Data is stored in Docker volumes (`app-data`, `letsencrypt`, `nginx-sites-available`, etc.). Map host ports 80/443 to this container instead of host nginx when migrating.

Inside Docker, `NGINX_RELOAD_MODE=signal` and `USE_SUDO=false` — no systemd or sudo required.

Let's Encrypt certificates renew automatically twice daily (`certbot-renew.timer` on native install, cron in Docker). Nginx reloads after a successful renewal.

## Installation on Ubuntu 24.04 (manual)

### 1. Install system packages

```bash
sudo bash deploy/install-prerequisites.sh
```

Or manually:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx python3.12-venv python3-pip \
  apache2-utils nodejs npm git openssl rsync ufw
```

### 2. Create service user and directories

```bash
sudo useradd --system --home /opt/reverse-proxy-admin --shell /usr/sbin/nologin nginx-admin
sudo mkdir -p /opt/reverse-proxy-admin /var/lib/reverse-proxy-admin/backups /etc/nginx-admin /etc/nginx/.htpasswd
sudo chown -R nginx-admin:nginx-admin /var/lib/reverse-proxy-admin
```

### 3. Deploy application files

```bash
sudo cp -r reverse-proxy-admin /opt/
sudo chown -R nginx-admin:nginx-admin /opt/reverse-proxy-admin
```

### 4. Backend setup

```bash
cd /opt/reverse-proxy-admin/backend
sudo -u nginx-admin python3 -m venv .venv
sudo -u nginx-admin .venv/bin/pip install -r requirements.txt
```

### 5. Configure environment

```bash
sudo cp /opt/reverse-proxy-admin/deploy/env.example /etc/nginx-admin/env
sudo chmod 600 /etc/nginx-admin/env
sudo nano /etc/nginx-admin/env
```

Set at minimum:

- `SECRET_KEY` (generate with `openssl rand -hex 32`; `install.sh` generates this automatically)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — set in `deploy/env.example` before first login
- `CERTBOT_EMAIL`
- `ALLOWED_IPS` (your internal subnet, e.g. `10.0.0.0/24`)

### 6. Build frontend

```bash
cd /opt/reverse-proxy-admin/frontend
npm ci
npm run build
```

Ensure `FRONTEND_DIST` points to `/opt/reverse-proxy-admin/frontend/dist` (default).

### 7. Grant least-privilege sudo

```bash
sudo cp /opt/reverse-proxy-admin/deploy/sudoers/nginx-admin /etc/sudoers.d/nginx-admin
sudo chmod 440 /etc/sudoers.d/nginx-admin
sudo visudo -cf /etc/sudoers.d/nginx-admin
```

Allowed commands for `nginx-admin`:

- `/usr/sbin/nginx -t`
- `/usr/sbin/nginx -t -c *`
- `/bin/systemctl is-active nginx`
- `/bin/systemctl status nginx --no-pager`
- `/bin/systemctl reload nginx`
- `/usr/bin/certbot *`

### 8. Grant nginx path permissions

Ensure `nginx-admin` can write site configs:

```bash
sudo chown -R nginx-admin:nginx-admin /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/.htpasswd
```

Alternatively, use ACLs if you prefer keeping root ownership.

### 9. Install systemd service

```bash
sudo cp /opt/reverse-proxy-admin/deploy/systemd/nginx-admin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nginx-admin
```

### 10. Expose UI internally via Nginx

```bash
sudo cp /opt/reverse-proxy-admin/deploy/nginx/admin-ui.conf.example /etc/nginx/sites-available/admin-ui.conf
sudo ln -sf /etc/nginx/sites-available/admin-ui.conf /etc/nginx/sites-enabled/admin-ui.conf
sudo nginx -t
sudo systemctl reload nginx
```

Access internally, for example: `https://<your-server-ip>:8443`

### Firewall (UFW)

If UFW is active, allow the admin UI port from your internal subnet:

```bash
sudo ufw allow from 10.0.0.0/24 to any port 8443 proto tcp comment 'Nginx Admin UI'
sudo ufw status
```

## Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ADMIN_PASSWORD=test-password
export DATABASE_URL=sqlite:///./dev.db
export USE_SUDO=false
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

Backend unit tests:

```bash
cd backend
pytest
```

Frontend unit tests:

```bash
cd frontend
npm install
npm test
```

CI runs both suites on every push to `master` and on pull requests via `.github/workflows/test.yml`.

## Backup and rollback

### Automatic rollback

Every config write/delete:

1. Creates a timestamped backup in `/var/lib/reverse-proxy-admin/backups/`
2. Applies the change
3. Runs `nginx -t`
4. Rolls back automatically if test fails
5. Reloads Nginx only when test succeeds

### Manual restore

```bash
sudo cp /var/lib/reverse-proxy-admin/backups/TIMESTAMP_app.conf /etc/nginx/sites-available/app.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Security notes

- Do not expose the admin UI publicly; keep it on internal IP/VPN only
- Use strong `SECRET_KEY` and admin password
- Review `ALLOWED_IPS` regularly
- Audit log available at `GET /api/audit` and **Audit** page (`/audit`)
- Security features (IP rules, geo blocking, WAF, threat feeds) at `/security`
- All subprocess calls use argument lists (`shell=False`)
- Input validation blocks shell injection patterns

## Deployment: GeoIP blocking

Geo blocking requires the nginx GeoIP2 module and a MaxMind GeoLite2 database:

```bash
sudo bash deploy/setup-geoip.sh
```

After setup, configure geo rules per proxy under **Security → Geo blocking**.

## Deployment: ModSecurity WAF

WAF integration requires ModSecurity and the OWASP CRS:

```bash
sudo bash deploy/setup-modsecurity.sh
```

Configure per-proxy WAF mode and profile under **Security → WAF**.

## API tokens

Create scoped Bearer tokens under **API Tokens** (admin only). Tokens authenticate against `/api/v1/*` endpoints.

Example:

```bash
curl -H "Authorization: Bearer rpa_..." https://127.0.0.1:8443/api/v1/proxies
```

Revoke unused tokens promptly. Token hashes are stored server-side; the plain token is shown once at creation.

## Backup

### Application database

```bash
sudo cp /var/lib/reverse-proxy-admin/app.db /var/lib/reverse-proxy-admin/backups/app-$(date +%Y%m%d).db
```

### Nginx configs and security snippets

Security include files live in `/var/lib/reverse-proxy-admin/security/` (IP rules, geo, WAF, threat feeds). Include this directory in your backup strategy alongside nginx site configs.

## API overview

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/proxies`
- `POST /api/proxies/{id}/enable|disable`
- `GET/POST/PUT/DELETE /api/security/ip-rules`, `/api/security/geo-rules`, `/api/security/threat-feeds`
- `GET/PUT /api/security/waf/{proxy_id}`, `GET /api/security/events`
- `GET /api/audit`, `GET /api/audit/export`, `GET /api/security/events/export`
- `GET /api/certificates`, `POST /api/certificates`, renew/dry-run actions
- `GET /api/logs/error`, `GET /api/logs/access`
- `GET /api/dashboard`, `GET /api/system/health`, nginx test/reload/status

## Troubleshooting

- Service logs: `journalctl -u nginx-admin -f`
- Certificate renewal timer: `systemctl status certbot-renew.timer` and `journalctl -u certbot-renew.service`
- Manual renewal test: `sudo bash /opt/reverse-proxy-admin/deploy/certbot-renew.sh` or `sudo certbot renew --dry-run`
- Permission errors: verify ownership/ACLs on nginx paths
- Certbot failures: ensure DNS/HTTP challenge reachable for public domains
- CSRF errors: ensure cookies are sent (`credentials: include`) and frontend uses same origin/proxy
