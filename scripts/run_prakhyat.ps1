param([ValidateSet('tests', 'demo', 'all')][string]$Mode = 'all')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Create the combined Python 3.12 environment described in docs/prakhyat-work.md first.'
}
Push-Location $projectRoot
try {
    if ($Mode -in @('tests', 'all')) {
        & $projectPython -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q', '--tb=short']))"
        if ($LASTEXITCODE -ne 0) { throw 'Tests failed; fixture run stopped.' }
    }
    if ($Mode -in @('demo', 'all')) {
        & $projectPython -m eval.pipeline --output-dir runs/prakhyat-fixture-demo
        if ($LASTEXITCODE -ne 0) { throw 'Fixture pipeline failed.' }
    }
} finally {
    Pop-Location
}
