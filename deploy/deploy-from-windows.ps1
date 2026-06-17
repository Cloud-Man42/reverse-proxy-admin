# Deploy reverse-proxy-admin to Ubuntu from Windows (interactive SSH password prompt)
# Usage: powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server user@your-server

param(
    [string]$Server = "user@your-server"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "Project root: $ProjectRoot"
Write-Host "Target server: $Server"
Write-Host ""
Write-Host "You will be prompted for your SSH password twice (upload + remote install)."
Write-Host ""

$Archive = Join-Path $env:TEMP "reverse-proxy-admin.tgz"
if (Test-Path $Archive) { Remove-Item $Archive -Force }

Push-Location (Split-Path $ProjectRoot -Parent)
try {
    tar -czf $Archive `
        --exclude="reverse-proxy-admin/frontend/node_modules" `
        --exclude="reverse-proxy-admin/backend/.venv" `
        --exclude="reverse-proxy-admin/backend/.pytest_cache" `
        --exclude="reverse-proxy-admin/.git" `
        reverse-proxy-admin
}
finally {
    Pop-Location
}

Write-Host "Uploading archive..."
scp $Archive "${Server}:/tmp/reverse-proxy-admin.tgz"

Write-Host "Running remote install (sudo password may be required on server)..."
ssh $Server @'
set -e
cd /tmp
rm -rf reverse-proxy-admin
tar -xzf reverse-proxy-admin.tgz
chmod +x reverse-proxy-admin/deploy/install.sh
sudo bash reverse-proxy-admin/deploy/install.sh
'@

Write-Host ""
Write-Host "Next steps on server:"
Write-Host "  1. ssh $Server"
Write-Host "  2. sudo nano /etc/nginx-admin/env"
Write-Host "     Set ADMIN_USERNAME, ADMIN_PASSWORD, ALLOWED_IPS, and SERVER_PUBLIC_IP"
Write-Host "  3. sudo systemctl restart nginx-admin"
Write-Host "  4. Open the admin UI on https://<your-server-ip>:8443 from your internal network"
Write-Host ""
