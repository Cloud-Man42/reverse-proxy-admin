#!/usr/bin/env bash
set -euo pipefail

# Install and start reverse-proxy-admin with Docker Compose.
# Usage: bash deploy/docker/install-docker.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine first."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is required (docker compose)."
  exit 1
fi

cd "${PROJECT_ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${SCRIPT_DIR}/env.docker.example" "${ENV_FILE}"
  SECRET_KEY="$(openssl rand -hex 32)"
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${ENV_FILE}"
  echo "Created ${ENV_FILE} from deploy/docker/env.docker.example"
fi

docker compose up -d --build

echo
echo "Reverse proxy admin is running in Docker."
echo "Admin UI: https://<host-ip>:8443"
echo "Log in with ADMIN_USERNAME / ADMIN_PASSWORD from .env (change under Users immediately)."
echo "Logs: docker compose logs -f reverse-proxy"
