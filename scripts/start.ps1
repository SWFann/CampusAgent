param(
    [ValidateSet("auto", "docker", "sqlite")]
    [string]$Mode = "auto",
    [int]$WebPort = 3000,
    [int]$ApiPort = 8000,
    [switch]$NoInstall,
    [switch]$NoSeed,
    [switch]$Smoke
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Write-Step($Message) {
    Write-Host "[CampusAgent] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[CampusAgent] $Message" -ForegroundColor Yellow
}

function Require-Command($Name, $Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. $Hint"
    }
}

function Test-PortInUse($Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Find-FreePort($Port) {
    while (Test-PortInUse $Port) {
        $Port += 1
    }
    return $Port
}

Require-Command "uv" "Install uv from https://docs.astral.sh/uv/."
Require-Command "corepack" "Install Node.js >= 18."
Require-Command "node" "Install Node.js >= 18."
Require-Command "git" "Install Git."

if ($Mode -eq "auto") {
    if ((Get-Command docker -ErrorAction SilentlyContinue) -and ((docker compose version) 2>$null)) {
        $Mode = "docker"
    } else {
        $Mode = "sqlite"
    }
}

if ($Mode -eq "docker") {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker mode requested, but docker is unavailable. Install Docker or run -Mode sqlite."
    }
    docker compose version | Out-Null
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

New-Item -ItemType Directory -Force ".local" | Out-Null
$env:UV_CACHE_DIR = Join-Path $Root ".local/uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Root ".local/uv-python"

Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
        return
    }
    $parts = $line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1], "Process")
}

if (-not $env:APP_ENV) { $env:APP_ENV = "development" }
if (-not $env:APP_DEBUG) { $env:APP_DEBUG = "false" }
if (-not $env:APP_SECRET) { $env:APP_SECRET = "dev-secret-key-change-in-production" }
if (-not $env:FIELD_ENCRYPTION_KEY) { $env:FIELD_ENCRYPTION_KEY = "dev-encryption-key-change-in-production" }
if (-not $env:MODEL_GATEWAY_API_KEY) { $env:MODEL_GATEWAY_API_KEY = "" }
if (-not $env:MODEL_GATEWAY_MODEL) { $env:MODEL_GATEWAY_MODEL = "step-3.7-flash" }
if (-not $env:MODEL_GATEWAY_TIMEOUT_MS) { $env:MODEL_GATEWAY_TIMEOUT_MS = "30000" }
if (-not $env:MODEL_GATEWAY_IS_EXTERNAL) { $env:MODEL_GATEWAY_IS_EXTERNAL = "true" }
if (-not $env:ENABLE_EXTERNAL_MODEL) { $env:ENABLE_EXTERNAL_MODEL = "false" }
$env:NEXT_PUBLIC_API_URL = "http://localhost:$ApiPort"

if ($Mode -eq "docker") {
    if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/campus_agent" }
    if (-not $env:REDIS_URL) { $env:REDIS_URL = "redis://localhost:6379/0" }
    if (-not $env:MODEL_GATEWAY_BASE_URL) { $env:MODEL_GATEWAY_BASE_URL = "http://localhost:8001" }
} else {
    $dbPath = (Resolve-Path ".local").Path + "\campus_agent.dev.db"
    $dbPath = $dbPath -replace "\\", "/"
    $env:DATABASE_URL = "sqlite:///$dbPath"
    if (-not $env:REDIS_URL) { $env:REDIS_URL = "redis://localhost:6379/1" }
    if (-not $env:MODEL_GATEWAY_BASE_URL) { $env:MODEL_GATEWAY_BASE_URL = "http://localhost:8001" }
}

if ($Smoke) {
    if (-not $NoInstall) {
        Write-Step "Installing dependencies if needed..."
        corepack pnpm install --frozen-lockfile
        uv sync --project apps/api --extra dev --frozen
    }
    Write-Step "Running demo smoke test..."
    uv run --project apps/api --extra dev --frozen python scripts/demo/run_demo_smoke.py
    exit $LASTEXITCODE
}

if (Test-PortInUse $ApiPort) {
    $nextApiPort = Find-FreePort $ApiPort
    Write-Warn "API port $ApiPort is already in use. Using $nextApiPort instead."
    $ApiPort = $nextApiPort
    $env:NEXT_PUBLIC_API_URL = "http://localhost:$ApiPort"
}
if (Test-PortInUse $WebPort) {
    $nextWebPort = Find-FreePort $WebPort
    Write-Warn "Web port $WebPort is already in use. Using $nextWebPort instead."
    $WebPort = $nextWebPort
}

if (-not $NoInstall) {
    Write-Step "Installing dependencies if needed..."
    corepack pnpm install --frozen-lockfile
    uv sync --project apps/api --extra dev --frozen
}

if ($Mode -eq "docker") {
    Write-Step "Starting Docker dependencies: postgres, redis, mock-model..."
    docker compose up -d postgres redis mock-model
} else {
    Write-Warn "Docker is unavailable or disabled. Using SQLite fallback."
    Write-Warn "Redis/model health may show degraded, but the website and API can start."
}

Write-Step "Running database migrations..."
Push-Location "apps/api"
uv run --project . --extra dev --frozen alembic -c alembic.ini upgrade head
Pop-Location

if (-not $NoSeed) {
    Write-Step "Seeding demo data..."
    uv run --project apps/api --extra dev --frozen python scripts/demo/seed_demo.py --json
}

Write-Step "Starting API on http://localhost:$ApiPort"
$api = Start-Process -FilePath "uv" -ArgumentList @("run", "--project", "apps/api", "--extra", "dev", "--frozen", "uvicorn", "src.main:app", "--app-dir", "apps/api", "--reload", "--port", "$ApiPort") -PassThru -NoNewWindow

Write-Step "Starting Web on http://localhost:$WebPort"
$webArgs = @("pnpm", "--filter", "@campus-agent/web", "dev", "--port", "$WebPort")
$web = Start-Process -FilePath "corepack" -ArgumentList $webArgs -PassThru -NoNewWindow

Write-Host ""
Write-Host "CampusAgent is starting."
Write-Host ""
Write-Host "Web:      http://localhost:$WebPort"
Write-Host "API:      http://localhost:$ApiPort"
Write-Host "API Docs: http://localhost:$ApiPort/docs"
Write-Host ""
Write-Host "Demo password: CampusAgentDemo2026!"
Write-Host "Press Ctrl+C, then stop child processes if needed."

Wait-Process -Id @($api.Id, $web.Id)
