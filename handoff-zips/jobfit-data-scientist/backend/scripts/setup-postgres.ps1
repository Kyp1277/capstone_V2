param(
    [string]$HostName = "127.0.0.1",
    [string]$Port = "5432",
    [string]$Database = "jobfit",
    [string]$User = "postgres",
    [string]$JobsTable = "jobs",
    [string]$PsqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

function Convert-SecureStringToPlainText {
    param([securestring]$SecureValue)

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if ($Database -notmatch "^[A-Za-z0-9_]+$") {
    throw "Nama database hanya boleh berisi huruf, angka, dan underscore."
}

if ($JobsTable -notmatch "^[A-Za-z0-9_]+$") {
    throw "Nama tabel hanya boleh berisi huruf, angka, dan underscore."
}

if (-not (Test-Path $PsqlPath)) {
    $psqlCommand = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $psqlCommand) {
        throw "psql.exe tidak ditemukan. Cek instalasi PostgreSQL atau isi parameter -PsqlPath."
    }
    $PsqlPath = $psqlCommand.Source
}

if (-not $Password) {
    $securePassword = Read-Host "Masukkan password PostgreSQL user $User" -AsSecureString
    $Password = Convert-SecureStringToPlainText $securePassword
}

$env:PGPASSWORD = $Password
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Resolve-Path (Join-Path $scriptRoot "..")
$projectRoot = Resolve-Path (Join-Path $backendRoot "..")
$codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path $codexPython) {
    $python = $codexPython
}
else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python tidak ditemukan."
    }
    $python = $pythonCommand.Source
}

Write-Host "Mengecek koneksi PostgreSQL..." -ForegroundColor Cyan
& $PsqlPath -h $HostName -p $Port -U $User -d postgres -v ON_ERROR_STOP=1 -c "SELECT 1;" | Out-Host

$exists = (& $PsqlPath -h $HostName -p $Port -U $User -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Database';").Trim()
if ($exists -ne "1") {
    Write-Host "Membuat database $Database..." -ForegroundColor Cyan
    & $PsqlPath -h $HostName -p $Port -U $User -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $Database;" | Out-Host
}
else {
    Write-Host "Database $Database sudah ada." -ForegroundColor Green
}

$databaseUrl = "postgresql://${User}:${Password}@${HostName}:${Port}/${Database}"
$envPath = Join-Path $backendRoot ".env"
$envContent = @(
    "DATABASE_URL=$databaseUrl",
    "JOBS_SOURCE=postgres",
    "JOBS_TABLE=$JobsTable",
    "HOST=127.0.0.1",
    "PORT=5000"
)
Set-Content -LiteralPath $envPath -Value $envContent -Encoding UTF8

Write-Host "Mengimport dataset jobs ke PostgreSQL..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    & $python "backend\scripts\import_jobs_to_postgres.py"
    & $python "backend\scripts\check_postgres_jobs.py"
}
finally {
    Pop-Location
}

Write-Host "Setup PostgreSQL JobFit selesai." -ForegroundColor Green
