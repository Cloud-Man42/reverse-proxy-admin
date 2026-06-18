# Deploy reverse-proxy-admin to Ubuntu from Windows (interactive SSH password prompt)
# Usage: powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1
#        powershell -ExecutionPolicy Bypass -File deploy\deploy-from-windows.ps1 -Server hm@192.168.50.54

param(
    [string]$Server = "hm@192.168.50.54"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "Project root: $ProjectRoot"
Write-Host "Target server: $Server"
Write-Host ""
Write-Host "You will be prompted for your SSH password (upload + remote full-sync)."
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

Write-Host "Running remote full-sync (sudo password may be required on server)..."
ssh $Server @'
set -e
cd /tmp
rm -rf reverse-proxy-admin
tar -xzf reverse-proxy-admin.tgz
find reverse-proxy-admin -name "*.sh" -exec sed -i 's/\r$//' {} +
chmod +x reverse-proxy-admin/deploy/full-sync.sh
sudo bash reverse-proxy-admin/deploy/full-sync.sh /tmp/reverse-proxy-admin
'@

Write-Host ""
Write-Host "Deploy complete."
Write-Host "Admin UI: https://192.168.50.54:8443"
Write-Host "Run flow diagnostics: ssh $Server 'sudo bash /opt/reverse-proxy-admin/deploy/diagnose-flow.sh code-tst sora.inacloud.net'"
Write-Host ""
