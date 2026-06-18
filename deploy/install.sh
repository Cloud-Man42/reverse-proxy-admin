#!/usr/bin/env bash
set -euo pipefail

# Run on Ubuntu 24.04 as a user with sudo access.
# Usage: sudo bash deploy/install.sh

APP_ROOT="/opt/reverse-proxy-admin"
ENV_FILE="/etc/nginx-admin/env"
SERVICE_USER="nginx-admin"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Checking system prerequisites"
bash "${SCRIPT_DIR}/install-prerequisites.sh"

echo "==> Creating service user and directories"
if ! id "${SERVICE_USER}" &>/dev/null; then
  useradd --system --home "${APP_ROOT}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
mkdir -p "${APP_ROOT}" /var/lib/reverse-proxy-admin/backups /var/lib/reverse-proxy-admin/certbot/work /var/lib/reverse-proxy-admin/certbot/logs /etc/nginx-admin /etc/nginx/.htpasswd /etc/letsencrypt/live
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/lib/reverse-proxy-admin

echo "==> Deploying application files"
rsync -a --delete \
  --exclude backend/.venv \
  --exclude backend/.pytest_cache \
  --exclude frontend/node_modules \
  --exclude .git \
  "${PROJECT_ROOT}/" "${APP_ROOT}/"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_ROOT}"

echo "==> Installing Python dependencies"
sudo -u "${SERVICE_USER}" python3 -m venv "${APP_ROOT}/backend/.venv"
sudo -u "${SERVICE_USER}" "${APP_ROOT}/backend/.venv/bin/pip" install -r "${APP_ROOT}/backend/requirements.txt"

echo "==> Building frontend"
cd "${APP_ROOT}/frontend"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build

echo "==> Configuring environment"
if [[ ! -f "${ENV_FILE}" ]]; then
  SECRET_KEY="$(openssl rand -hex 32)"
  cp "${APP_ROOT}/deploy/env.example" "${ENV_FILE}"
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE} from deploy/env.example (default admin credentials — change after first login)."
fi

echo "==> Installing sudoers"
cp "${APP_ROOT}/deploy/sudoers/nginx-admin" /etc/sudoers.d/nginx-admin
sed -i 's/\r$//' /etc/sudoers.d/nginx-admin
chmod 440 /etc/sudoers.d/nginx-admin
visudo -cf /etc/sudoers.d/nginx-admin

echo "==> Setting nginx path permissions"
chown -R "${SERVICE_USER}:${SERVICE_USER}" /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/.htpasswd

echo "==> Installing systemd service"
sed -i 's/\r$//' "${APP_ROOT}/deploy/systemd/nginx-admin.service"
cp "${APP_ROOT}/deploy/systemd/nginx-admin.service" /etc/systemd/system/nginx-admin.service
systemctl daemon-reload
systemctl enable nginx-admin

systemctl restart nginx-admin

echo "==> Installing admin UI nginx vhost (if missing)"
if [[ ! -f /etc/nginx/sites-available/admin-ui.conf ]]; then
  if [[ ! -f /etc/ssl/certs/nginx-admin.crt ]]; then
    openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
      -keyout /etc/ssl/private/nginx-admin.key \
      -out /etc/ssl/certs/nginx-admin.crt \
      -subj "/CN=nginx-admin.local"
    chmod 600 /etc/ssl/private/nginx-admin.key
  fi
  cp "${APP_ROOT}/deploy/nginx/admin-ui.conf.example" /etc/nginx/sites-available/admin-ui.conf
  ln -sf /etc/nginx/sites-available/admin-ui.conf /etc/nginx/sites-enabled/admin-ui.conf
fi

mkdir -p /etc/nginx/conf.d
cp "${APP_ROOT}/deploy/nginx/proxy-debug-log.conf" /etc/nginx/conf.d/proxy-debug-log.conf
sed -i 's/\r$//' /etc/nginx/conf.d/proxy-debug-log.conf

nginx -t
systemctl reload nginx

echo "==> Configuring automatic certificate renewal"
bash "${APP_ROOT}/deploy/setup-certbot-renewal.sh" "${APP_ROOT}"

echo "==> Configuring firewall for admin UI"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  # Replace 10.0.0.0/24 with your internal admin subnet(s)
  ufw allow from 10.0.0.0/24 to any port 8443 proto tcp comment "Nginx Admin UI" || true
fi

DEFAULT_ADMIN_USERNAME="$(grep '^ADMIN_USERNAME=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"')"
DEFAULT_ADMIN_PASSWORD="$(grep '^ADMIN_PASSWORD=' "${ENV_FILE}" | cut -d= -f2- | tr -d '"')"

echo
echo "Deployment complete."
echo "Default admin login (change immediately after first login):"
echo "  Username: ${DEFAULT_ADMIN_USERNAME}"
echo "  Password: ${DEFAULT_ADMIN_PASSWORD}"
echo "Change password in Admin UI → Users, or edit ${ENV_FILE} before first start on a new server."
echo "Configure TLS in /etc/nginx/sites-available/admin-ui.conf if needed."
echo "Open https://<your-server-ip>:8443 from your internal network"
