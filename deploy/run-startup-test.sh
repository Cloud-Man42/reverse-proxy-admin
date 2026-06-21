#!/bin/bash
set -euo pipefail
set -a
source /etc/nginx-admin/env
set +a
sudo -u nginx-admin -E bash -c 'cd /opt/reverse-proxy-admin/backend && . .venv/bin/activate && python startup_test.py'
