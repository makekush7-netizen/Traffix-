param([int]$Port=8004)
$ErrorActionPreference='Stop'
$TraffixRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $TraffixRoot
Write-Host "Experimental response view: http://localhost:$Port/response"
& (Join-Path $TraffixRoot '.venv/Scripts/python.exe') -m uvicorn backend.harness.response_lab:create_response_app --factory --host 0.0.0.0 --port $Port --workers 1
