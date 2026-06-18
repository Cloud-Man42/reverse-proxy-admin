#!/bin/sh
set -e

# Certbot deploy hook — reload nginx after a successful certificate renewal.

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet nginx 2>/dev/null; then
  systemctl reload nginx
elif command -v nginx >/dev/null 2>&1; then
  nginx -s reload
fi
