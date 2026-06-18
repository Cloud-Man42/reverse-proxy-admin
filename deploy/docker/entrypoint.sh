#!/usr/bin/env bash
set -euo pipefail

ADMIN_UI_CERT="/etc/ssl/certs/nginx-admin.crt"
ADMIN_UI_KEY="/etc/ssl/private/nginx-admin.key"

mkdir -p /var/lib/reverse-proxy-admin/backups \
    /var/lib/reverse-proxy-admin/certbot/work \
    /var/lib/reverse-proxy-admin/certbot/logs \
    /etc/nginx/.htpasswd \
    /etc/nginx/sites-available \
    /etc/nginx/sites-enabled \
    /etc/letsencrypt/live \
    /var/log/nginx \
    /etc/ssl/certs \
    /etc/ssl/private

if [[ ! -f "${ADMIN_UI_CERT}" || ! -f "${ADMIN_UI_KEY}" ]]; then
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "${ADMIN_UI_KEY}" \
    -out "${ADMIN_UI_CERT}" \
    -subj "/CN=nginx-admin.local"
  chmod 600 "${ADMIN_UI_KEY}"
fi

if [[ ! -f /etc/nginx/sites-available/admin-ui.conf ]]; then
  cp /app/deploy/docker/admin-ui.conf /etc/nginx/sites-available/admin-ui.conf
fi

if [[ ! -L /etc/nginx/sites-enabled/admin-ui.conf ]]; then
  ln -sf /etc/nginx/sites-available/admin-ui.conf /etc/nginx/sites-enabled/admin-ui.conf
fi

bash /app/deploy/setup-certbot-renewal.sh /app

nginx -t

exec "$@"
