param([int]$Port=8002)
$ErrorActionPreference='Stop'
$TraffixRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $TraffixRoot
$TraffixPython=Join-Path $TraffixRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $TraffixPython)) { Write-Host 'FAIL: .venv missing'; exit 1 }
& $TraffixPython scripts/demo_check.py --port $Port
exit $LASTEXITCODE
