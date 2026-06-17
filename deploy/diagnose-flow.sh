#!/bin/bash
set -euo pipefail

PROXY_ID="${1:-code-tst}"
DOMAIN="${2:-sora.inacloud.net}"
APP_ROOT="/opt/reverse-proxy-admin"
VENV="${APP_ROOT}/backend/.venv/bin/python"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/diagnose-flow.sh [proxy_id] [domain]"
  exit 1
fi

echo "==> Certificate files"
sudo -u nginx-admin sudo test -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" && echo "fullchain: OK" || echo "fullchain: MISSING"
sudo -u nginx-admin sudo test -f "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" && echo "privkey: OK" || echo "privkey: MISSING"

echo
echo "==> Certbot list"
sudo -u nginx-admin sudo certbot certificates --config-dir /etc/letsencrypt | sed -n "/${DOMAIN}/,/^$/p" || true

echo
echo "==> Flow test checks as nginx-admin"
sudo -u nginx-admin "${VENV}" - "${PROXY_ID}" <<'PY'
import sys

sys.path.insert(0, "/opt/reverse-proxy-admin/backend")

from app.config import Settings
from app.schemas import ProxyAppUpdate
from app.services.cert_paths import certificate_exists, certificate_exists_message
from app.services.proxy_service import ProxyService
from app.services.traffic_flow_service import TrafficFlowService

proxy_id = sys.argv[1]
settings = Settings()
proxy = ProxyService(settings).get_proxy(proxy_id)
if not proxy:
    print(f"Proxy not found: {proxy_id}")
    sys.exit(1)

payload = ProxyAppUpdate(
    name=proxy.name,
    domains=proxy.domains,
    routes=proxy.routes,
    custom_headers=proxy.custom_headers,
    max_body_size=proxy.max_body_size,
    basic_auth_enabled=proxy.basic_auth_enabled,
    force_https=proxy.force_https,
    enabled=proxy.enabled,
)
domain = proxy.domains[0]
print(f"Proxy: {proxy_id} domain={domain} force_https={proxy.force_https}")
print(f"certificate_exists: {certificate_exists(settings, domain)}")
print(f"certificate_message: {certificate_exists_message(settings, domain)}")

result = TrafficFlowService(settings).test_traffic_flow(payload)
print(f"summary: {result.summary}")
for check in result.checks:
    status = "OK" if check.success else "FAIL"
    print(f"[{status}] {check.name}: {check.message}")
PY
