#!/usr/bin/env bash
set -euo pipefail

# Install ModSecurity v3 for nginx and OWASP CRS for per-proxy WAF in the Admin UI.
# Usage: sudo bash deploy/setup-modsecurity.sh [app_root]

APP_ROOT="${1:-/opt/reverse-proxy-admin}"
MODSEC_DIR="/etc/nginx/modsecurity"
CRS_BASE="${MODSEC_DIR}/crs-base.conf"
CORE_CONF="${MODSEC_DIR}/modsecurity-core.conf"
AUDIT_LOG="/var/log/nginx/modsec_audit.log"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/setup-modsecurity.sh"
  exit 1
fi

echo "==> Installing ModSecurity nginx module and OWASP CRS"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y libnginx-mod-http-modsecurity modsecurity-crs

echo "==> Ensuring ModSecurity module is enabled"
if [[ ! -e /etc/nginx/modules-enabled/50-mod-http-modsecurity.conf ]]; then
  ln -sf /usr/share/nginx/modules-available/mod-http-modsecurity.conf \
    /etc/nginx/modules-enabled/50-mod-http-modsecurity.conf
fi

echo "==> Preparing ModSecurity core configuration"
mkdir -p "${MODSEC_DIR}"
if [[ ! -f /etc/nginx/modsecurity.conf ]]; then
  cp /usr/share/nginx/docs/modsecurity/modsecurity.conf /etc/nginx/modsecurity.conf
fi
if [[ ! -f /etc/nginx/unicode.mapping ]]; then
  cp /usr/share/nginx/docs/modsecurity/unicode.mapping /etc/nginx/unicode.mapping
fi

# Per-proxy snippets set SecRuleEngine; keep core rules without a global engine mode.
grep -v '^SecRuleEngine ' /etc/nginx/modsecurity.conf >"${CORE_CONF}.tmp"
mv "${CORE_CONF}.tmp" "${CORE_CONF}"

install -m 644 "${APP_ROOT}/deploy/nginx/modsecurity-crs-base.conf" "${CRS_BASE}"
sed -i 's/\r$//' "${CRS_BASE}"

echo "==> Ensuring CRS local overrides exist"
mkdir -p /etc/modsecurity/crs
touch /etc/modsecurity/crs/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf
touch /etc/modsecurity/crs/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
if [[ ! -f /etc/modsecurity/crs/crs-setup.conf ]]; then
  cp /usr/share/modsecurity-crs/crs-setup.conf.example /etc/modsecurity/crs/crs-setup.conf
fi

echo "==> Preparing ModSecurity runtime directories"
mkdir -p /tmp/modsecurity/tmp /tmp/modsecurity/data
chown www-data:www-data /tmp/modsecurity/tmp /tmp/modsecurity/data
touch "${AUDIT_LOG}"
chown www-data:adm "${AUDIT_LOG}"
chmod 640 "${AUDIT_LOG}"

echo "==> Validating nginx configuration"
nginx -t
systemctl reload nginx

echo
echo "ModSecurity WAF is ready."
echo "  CRS base: ${CRS_BASE}"
echo "  Audit log: ${AUDIT_LOG}"
echo "Enable WAF per proxy under Security -> WAF in the Admin UI, then redeploy the proxy."
