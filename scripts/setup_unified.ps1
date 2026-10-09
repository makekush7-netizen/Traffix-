param([Parameter(Mandatory=$true)][string]$Python312)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    & $Python312 -c "import sys; assert sys.version_info[:2] == (3,12), 'Use Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw 'Unsupported Python runtime' }
    & $Python312 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    & ./.venv/Scripts/python.exe -m pip install -r backend/simulation/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & ./.venv/Scripts/python.exe -c "from scripts.run_unified import prepare_environment; import subprocess; h=prepare_environment(); subprocess.run([str(h/'bin'/'sumo.exe'),'--version'],check=True)"
    if ($LASTEXITCODE -ne 0) { throw 'SUMO runtime validation failed' }
    Write-Output 'Setup complete. Configure TRAFFIX_ACCOUNTS, then run .venv/Scripts/python.exe -m scripts.run_unified.'
} finally { Pop-Location }
