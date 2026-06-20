#!/usr/bin/env bash
set -euo pipefail

# Install or refresh HTTPS admin UI nginx vhost (port 8443).
# Usage: sudo bash deploy/setup-admin-ui-https.sh [app_root]

APP_ROOT="${1:-/opt/reverse-proxy-admin}"
ENV_FILE="/etc/nginx-admin/env"
ADMIN_UI_CONF="/etc/nginx/sites-available/admin-ui.conf"
CERT="/etc/ssl/certs/nginx-admin.crt"
KEY="/etc/ssl/private/nginx-admin.key"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

SERVER_IP="203.0.113.1"
ADMIN_PORT=8443
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source <(grep -E '^(SERVER_PUBLIC_IP|ADMIN_UI_PORT)=' "${ENV_FILE}" | sed 's/\r$//')
fi
if [[ -z "${SERVER_IP}" || "${SERVER_IP}" == "203.0.113.1" ]]; then
  SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi
ADMIN_PORT="${ADMIN_UI_PORT:-8443}"

ALLOW_LINES=(
  "    allow 127.0.0.1;"
  "    allow ::1;"
)
if [[ -f "${ENV_FILE}" ]] && grep -q '^ALLOWED_IPS=' "${ENV_FILE}"; then
  IPS_CLEAN="$(grep '^ALLOWED_IPS=' "${ENV_FILE}" | cut -d= -f2- | tr -d '[]"' | tr ',' ' ')"
  for entry in ${IPS_CLEAN}; do
    entry="$(echo "${entry}" | xargs)"
    [[ -n "${entry}" ]] || continue
    ALLOW_LINES+=("    allow ${entry};")
  done
else
  ALLOW_LINES+=("    allow 10.0.0.0/8;")
  ALLOW_LINES+=("    allow 172.16.0.0/12;")
  ALLOW_LINES+=("    allow 192.168.0.0/16;")
fi
ALLOW_LINES+=("    deny all;")

if [[ ! -f "${CERT}" || ! -f "${KEY}" ]]; then
  echo "==> Creating self-signed certificate for admin UI"
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "${KEY}" \
    -out "${CERT}" \
    -subj "/CN=reverse-proxy-admin/O=In a Cloud"
  chmod 600 "${KEY}"
fi

{
  echo "# Managed by reverse-proxy-admin deploy/setup-admin-ui-https.sh"
  echo "# Admin UI is HTTPS-only on port ${ADMIN_PORT}."
  echo "server {"
  echo "    listen ${SERVER_IP}:${ADMIN_PORT} ssl;"
  echo "    server_name nginx-admin.local;"
  echo ""
  echo "    ssl_certificate     ${CERT};"
  echo "    ssl_certificate_key ${KEY};"
  echo "    ssl_protocols TLSv1.2 TLSv1.3;"
  echo "    ssl_prefer_server_ciphers off;"
  echo "    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;"
  echo ""
  for line in "${ALLOW_LINES[@]}"; do
    echo "${line}"
  done
  echo ""
  echo "    location / {"
  echo "        proxy_pass http://127.0.0.1:8080;"
  echo "        proxy_set_header Host \$host;"
  echo "        proxy_set_header X-Real-IP \$remote_addr;"
  echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;"
  echo "        proxy_set_header X-Forwarded-Proto https;"
  echo "    }"
  echo "}"
} > "${ADMIN_UI_CONF}"

ln -sf "${ADMIN_UI_CONF}" /etc/nginx/sites-enabled/admin-ui.conf
nginx -t
systemctl reload nginx

echo "Admin UI HTTPS vhost configured at https://${SERVER_IP}:${ADMIN_PORT}"
