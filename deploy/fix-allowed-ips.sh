#!/bin/bash
# Example helper — edit ALLOWED_IPS to match your internal subnets before running.
set -euo pipefail

ENV_FILE="/etc/nginx-admin/env"
ALLOWED_IPS="${ALLOWED_IPS:-[\"127.0.0.1\",\"::1\",\"10.0.0.0/24\"]}"

sed -i "s|^ALLOWED_IPS=.*|ALLOWED_IPS=${ALLOWED_IPS}|" "${ENV_FILE}"
grep ALLOWED_IPS "${ENV_FILE}"
systemctl restart nginx-admin
systemctl is-active nginx-admin
