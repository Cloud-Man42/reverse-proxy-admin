#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash extend-disk.sh"
  exit 1
fi

echo "==> Rescanning disk"
echo 1 > /sys/class/block/sda/device/rescan 2>/dev/null || true
sleep 1

if ! command -v growpart >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq cloud-guest-utils
fi

echo "==> Before"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT /dev/sda
df -h /
pvs
vgs

echo "==> Growing partition /dev/sda3"
growpart /dev/sda 3

echo "==> Resizing physical volume"
pvresize /dev/sda3

echo "==> Extending logical volume and filesystem"
lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
resize2fs /dev/ubuntu-vg/ubuntu-lv

echo "==> After"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT /dev/sda
df -h /
pvs
vgs

echo "Disk extension complete."
