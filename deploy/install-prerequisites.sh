#!/usr/bin/env bash
set -euo pipefail

# Install Nginx, Certbot, and other OS packages used by reverse-proxy-admin.
# Idempotent: only installs packages/commands that are missing.
#
# Usage:
#   sudo bash deploy/install-prerequisites.sh

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install-prerequisites.sh"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Debian/Ubuntu (apt-get required)."
  exit 1
fi

has_package() {
  dpkg -s "$1" >/dev/null 2>&1
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

missing_packages=()

require_package() {
  local pkg="$1"
  if ! has_package "${pkg}"; then
    missing_packages+=("${pkg}")
  fi
}

require_command_package() {
  local cmd="$1"
  local pkg="$2"
  if ! has_command "${cmd}" && ! has_package "${pkg}"; then
    missing_packages+=("${pkg}")
  fi
}

# Reverse proxy stack
require_package nginx
require_package certbot
require_package python3-certbot-nginx

# Backend / tooling
require_command_package python3 python3
require_command_package pip3 python3-pip
require_command_package htpasswd apache2-utils
require_command_package node nodejs
require_command_package npm npm
require_command_package openssl openssl
require_command_package rsync rsync
require_command_package git git

# Optional but used by the admin UI (firewall status)
require_command_package ufw ufw

# Python venv module (Ubuntu 24.04 package name)
if ! python3 -m venv -h >/dev/null 2>&1; then
  if has_package python3.12-venv; then
    :
  elif has_package python3-venv; then
    :
  else
    if apt-cache show python3.12-venv >/dev/null 2>&1; then
      missing_packages+=("python3.12-venv")
    else
      missing_packages+=("python3-venv")
    fi
  fi
fi

# Deduplicate missing package list
if [[ ${#missing_packages[@]} -gt 0 ]]; then
  mapfile -t missing_packages < <(printf '%s\n' "${missing_packages[@]}" | awk '!seen[$0]++')
fi

if [[ ${#missing_packages[@]} -gt 0 ]]; then
  echo "==> Installing missing packages: ${missing_packages[*]}"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing_packages[@]}"
else
  echo "==> All required OS packages are already installed"
fi

SERVICE_USER="nginx-admin"

echo "==> Ensuring shared directories exist"
mkdir -p /etc/letsencrypt/live
mkdir -p /var/lib/letsencrypt
mkdir -p /var/lib/reverse-proxy-admin/certbot/work /var/lib/reverse-proxy-admin/certbot/logs
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/lib/reverse-proxy-admin/certbot 2>/dev/null || true

if has_command nginx; then
  echo "==> Ensuring nginx service is enabled"
  systemctl enable nginx >/dev/null 2>&1 || true
  if ! systemctl is-active --quiet nginx; then
    systemctl start nginx || true
  fi
fi

echo "==> Verifying required commands"
required_commands=(nginx certbot htpasswd node npm python3 openssl rsync git)
failed=0
for cmd in "${required_commands[@]}"; do
  if ! has_command "${cmd}"; then
    echo "ERROR: required command not available: ${cmd}" >&2
    failed=1
  fi
done

if ! python3 -m venv -h >/dev/null 2>&1; then
  echo "ERROR: python3 venv module is not available" >&2
  failed=1
fi

if [[ "${failed}" -ne 0 ]]; then
  exit 1
fi

echo "Prerequisites check complete."
