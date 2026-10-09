param([ValidateSet('tests', 'demo', 'all')][string]$Mode = 'all')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create the Python 3.12 virtual environment described in README.md first.'
}
Push-Location $projectRoot
try {
    if ($Mode -in @('tests', 'all')) {
        & $projectPython -m pytest -q --tb=short
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; fixture run stopped.' }
    }
    if ($Mode -in @('demo', 'all')) {
        & $projectPython -m eval.pipeline --output-dir artifacts/fixture-demo
        if ($LASTEXITCODE -ne 0) { throw 'Fixture pipeline failed.' }
    }
} finally {
    Pop-Location
}
