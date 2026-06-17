#!/bin/bash
set -euo pipefail

APP_ROOT="/opt/reverse-proxy-admin"
ENV_FILE="/etc/nginx-admin/env"
SERVICE_USER="nginx-admin"
SOURCE="${1:-/tmp/reverse-proxy-admin}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/full-sync.sh [source_dir]"
  exit 1
fi

echo "==> Syncing application from ${SOURCE}"
rsync -a --delete \
  --exclude backend/.venv \
  --exclude backend/.pytest_cache \
  --exclude frontend/node_modules \
  --exclude .git \
  "${SOURCE}/" "${APP_ROOT}/"
find "${APP_ROOT}" -name "*.sh" -exec sed -i 's/\r$//' {} +

echo "==> Fixing ownership"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_ROOT}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/lib/reverse-proxy-admin

echo "==> Ensuring Python venv and dependencies"
if [[ ! -d "${APP_ROOT}/backend/.venv" ]]; then
  sudo -u "${SERVICE_USER}" python3 -m venv "${APP_ROOT}/backend/.venv"
fi
sudo -u "${SERVICE_USER}" "${APP_ROOT}/backend/.venv/bin/pip" install -r "${APP_ROOT}/backend/requirements.txt" -q

echo "==> Building frontend on server"
cd "${APP_ROOT}/frontend"
if [[ -f package-lock.json ]]; then
  npm ci --silent
else
  npm install --silent
fi
npm run build
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_ROOT}/frontend/dist"

echo "==> Updating environment file"
if ! grep -q '^SERVER_PUBLIC_IP=' "${ENV_FILE}"; then
  SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -z "${SERVER_IP}" ]]; then
    SERVER_IP="203.0.113.1"
  fi
  echo "SERVER_PUBLIC_IP=${SERVER_IP}" >> "${ENV_FILE}"
fi
if ! grep -q '^SERVER_HOSTNAME=' "${ENV_FILE}"; then
  echo "SERVER_HOSTNAME=$(hostname -s 2>/dev/null || echo reverse-proxy)" >> "${ENV_FILE}"
fi
if ! grep -q '^NETWORK_EXPOSED_PORTS=' "${ENV_FILE}"; then
  echo 'NETWORK_EXPOSED_PORTS=[80,443,8443]' >> "${ENV_FILE}"
fi
chmod 600 "${ENV_FILE}"

echo "==> Fixing nginx log read permissions"
usermod -aG adm "${SERVICE_USER}" 2>/dev/null || true
for logfile in /var/log/nginx/error.log /var/log/nginx/access.log; do
  if [[ -f "${logfile}" ]]; then
    setfacl -m "u:${SERVICE_USER}:r" "${logfile}" 2>/dev/null || chmod o+r "${logfile}" || true
  fi
done

echo "==> Allowing nginx-admin to read Let's Encrypt certificates"
if [[ -d /etc/letsencrypt/live ]]; then
  setfacl -R -m "u:${SERVICE_USER}:rx" /etc/letsencrypt/live 2>/dev/null || true
  setfacl -d -m "u:${SERVICE_USER}:rx" /etc/letsencrypt/live 2>/dev/null || true
fi
if [[ -d /etc/letsencrypt/archive ]]; then
  setfacl -R -m "u:${SERVICE_USER}:r" /etc/letsencrypt/archive 2>/dev/null || true
  setfacl -d -m "u:${SERVICE_USER}:r" /etc/letsencrypt/archive 2>/dev/null || true
fi

echo "==> Installing sudoers"
sed -i 's/\r$//' "${APP_ROOT}/deploy/sudoers/nginx-admin"
cp "${APP_ROOT}/deploy/sudoers/nginx-admin" /etc/sudoers.d/nginx-admin
chmod 440 /etc/sudoers.d/nginx-admin
visudo -cf /etc/sudoers.d/nginx-admin

echo "==> Installing systemd unit"
sed -i 's/\r$//' "${APP_ROOT}/deploy/systemd/nginx-admin.service"
cp "${APP_ROOT}/deploy/systemd/nginx-admin.service" /etc/systemd/system/nginx-admin.service
systemctl daemon-reload

echo "==> Ensuring letsencrypt dir for systemd namespace"
mkdir -p /etc/letsencrypt/live
chown root:root /etc/letsencrypt/live

echo "==> Installing proxy debug log format"
mkdir -p /etc/nginx/conf.d
cp "${APP_ROOT}/deploy/nginx/proxy-debug-log.conf" /etc/nginx/conf.d/proxy-debug-log.conf
sed -i 's/\r$//' /etc/nginx/conf.d/proxy-debug-log.conf
nginx -t
systemctl reload nginx

echo "==> Restarting services"
systemctl restart nginx-admin
sleep 2
systemctl is-active nginx-admin
curl -s http://127.0.0.1:8080/api/health

echo
echo "Full sync complete."
