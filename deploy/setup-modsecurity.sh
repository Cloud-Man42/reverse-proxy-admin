#!/usr/bin/env bash
# Stub: install ModSecurity and OWASP CRS for WAF integration.
set -euo pipefail

echo "ModSecurity setup stub"
echo "Install libnginx-mod-security2 and OWASP ModSecurity CRS:"
echo "  sudo apt install -y libnginx-mod-security2 modsecurity-crs"
echo "  sudo cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf"
echo "  # Enable SecRuleEngine DetectionOnly or On per proxy via Admin UI"
echo "  sudo nginx -t && sudo systemctl reload nginx"
