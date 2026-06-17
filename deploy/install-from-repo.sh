#!/usr/bin/env bash
set -euo pipefail

# Install reverse-proxy-admin from a cloned Git repository on Ubuntu/Debian.
# Installs OS prerequisites only when missing, then deploys the application.
#
# Usage (on the server, from repo root):
#   git clone https://github.com/Cloud-Man42/reverse-proxy-admin.git
#   cd reverse-proxy-admin
#   sudo bash deploy/install-from-repo.sh

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install-from-repo.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find "${SCRIPT_DIR}" -name "*.sh" -exec sed -i 's/\r$//' {} +

bash "${SCRIPT_DIR}/install-prerequisites.sh"
bash "${SCRIPT_DIR}/install.sh"
