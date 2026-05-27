$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$localPackages = Join-Path $projectRoot ".codex-python-packages"
$codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $localPackages) {
    $env:PYTHONPATH = $localPackages
}

if (Test-Path $codexPython) {
    & $codexPython (Join-Path $PSScriptRoot "api.py")
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source (Join-Path $PSScriptRoot "api.py")
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source (Join-Path $PSScriptRoot "api.py")
    exit $LASTEXITCODE
}

Write-Error "Python tidak ditemukan. Install Python 3.11+ atau jalankan dari Codex runtime."
