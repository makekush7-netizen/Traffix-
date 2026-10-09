param([int]$Port=8002)
$ErrorActionPreference='Stop'
$TraffixRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $TraffixRoot
$TraffixPython=Join-Path $TraffixRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $TraffixPython)) { throw 'Create .venv and install backend/harness/requirements.txt first.' }
Write-Host "Traffix dashboard: http://localhost:$Port/dashboard"
Write-Host "Driver app: http://<laptop-Wi-Fi-IP>:$Port/driver"
& $TraffixPython -m uvicorn backend.harness.app:create_demo_app --factory --host 0.0.0.0 --port $Port --workers 1
