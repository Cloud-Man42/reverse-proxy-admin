#!/usr/bin/env bash
set -euo pipefail

# Renew Let's Encrypt certificates using the same paths as reverse-proxy-admin.
# Invoked by systemd timer (native install) or cron (Docker).

CONFIG_DIR="${CERTBOT_CONFIG_DIR:-/etc/letsencrypt}"
WORK_DIR="${CERTBOT_WORK_DIR:-/var/lib/reverse-proxy-admin/certbot/work}"
LOGS_DIR="${CERTBOT_LOGS_DIR:-/var/lib/reverse-proxy-admin/certbot/logs}"

mkdir -p "${WORK_DIR}" "${LOGS_DIR}"

/usr/bin/certbot renew \
  --config-dir "${CONFIG_DIR}" \
  --work-dir "${WORK_DIR}" \
  --logs-dir "${LOGS_DIR}" \
  --quiet

# /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh runs when a cert is renewed.
