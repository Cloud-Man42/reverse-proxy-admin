#!/usr/bin/env bash
set -euo pipefail

# Install automatic Let's Encrypt renewal (systemd timer on native, cron in Docker).
# Usage: sudo bash deploy/setup-certbot-renewal.sh [app_root]

APP_ROOT="${1:-/opt/reverse-proxy-admin}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/setup-certbot-renewal.sh"
  exit 1
fi

echo "==> Installing Certbot deploy hook (reload nginx after renewal)"
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
install -m 755 "${APP_ROOT}/deploy/letsencrypt/reload-nginx.sh" /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
chmod +x "${APP_ROOT}/deploy/certbot-renew.sh"

if [[ -d /run/systemd/system ]] && command -v systemctl >/dev/null 2>&1; then
  echo "==> Installing systemd timer for automatic renewal"
  sed -i 's/\r$//' "${APP_ROOT}/deploy/systemd/certbot-renew.service"
  sed -i 's/\r$//' "${APP_ROOT}/deploy/systemd/certbot-renew.timer"
  cp "${APP_ROOT}/deploy/systemd/certbot-renew.service" /etc/systemd/system/certbot-renew.service
  cp "${APP_ROOT}/deploy/systemd/certbot-renew.timer" /etc/systemd/system/certbot-renew.timer
  systemctl daemon-reload

  if systemctl list-unit-files certbot.timer >/dev/null 2>&1; then
    systemctl disable --now certbot.timer 2>/dev/null || true
  fi

  systemctl enable certbot-renew.timer
  systemctl start certbot-renew.timer
  systemctl is-active certbot-renew.timer
  echo "Next renewal check: $(systemctl list-timers certbot-renew.timer --no-pager | tail -1 || true)"
elif command -v cron >/dev/null 2>&1 && [[ -f "${APP_ROOT}/deploy/docker/certbot-renew.cron" ]]; then
  echo "==> Installing cron job for automatic renewal (Docker)"
  install -m 644 "${APP_ROOT}/deploy/docker/certbot-renew.cron" /etc/cron.d/certbot-renew
  if pgrep -x cron >/dev/null 2>&1 || pgrep -x crond >/dev/null 2>&1; then
    :
  elif command -v cron >/dev/null 2>&1; then
    cron || true
  fi
else
  echo "WARNING: No systemd or cron available — configure renewal manually."
fi

echo "Automatic certificate renewal configured."
