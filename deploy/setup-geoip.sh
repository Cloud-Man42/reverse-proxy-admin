#!/usr/bin/env bash
# Stub: install GeoIP2 database and nginx module for geo blocking.
set -euo pipefail

echo "GeoIP setup stub"
echo "Install libnginx-mod-http-geoip2 and download GeoLite2-Country.mmdb to /usr/share/GeoIP/"
echo "Example:"
echo "  sudo apt install -y libnginx-mod-http-geoip2"
echo "  sudo mkdir -p /usr/share/GeoIP"
echo "  # Download GeoLite2-Country.mmdb from MaxMind and place at /usr/share/GeoIP/GeoLite2-Country.mmdb"
echo "  sudo nginx -t && sudo systemctl reload nginx"
