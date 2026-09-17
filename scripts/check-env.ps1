# ============================================================
# SIH26062 — Safe Development Environment Configuration Checker
# Usage: ./scripts/check-env.ps1
# Checks that required development variables exist without exposing secrets.
# ============================================================

param (
    [string]$EnvFile = ".env"
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SIH26062 - Environment Configuration Check" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$envVars = @{}

# 1. Load from .env file if present
$envFilePath = Join-Path $repoRoot $EnvFile
if (Test-Path $envFilePath) {
    Write-Host "Found $EnvFile file. Reading variable presence..." -ForegroundColor Gray
    Get-Content $envFilePath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and (-not $line.StartsWith("#")) -and ($line -match "^([A-Za-z0-9_]+)=(.*)$")) {
            $key = $matches[1]
            $val = $matches[2].Trim()
            if ($val -ne "") {
                $envVars[$key] = $true
            }
        }
    }
} else {
    Write-Host "No $EnvFile file found in repository root. Checking process environment variables..." -ForegroundColor Gray
}

# 2. Check process environment variables as fallback
$requiredVars = @("SUPABASE_URL", "API_BASE_URL")
$missing = @()

foreach ($var in $requiredVars) {
    $hasInFile = $envVars.ContainsKey($var)
    $hasInProcess = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($var))
    if (-not $hasInFile -and -not $hasInProcess) {
        $missing += $var
    }
}

# Check for database URL (either DATABASE_URL or SUPABASE_DB_URL must be present)
$hasDbUrl = ($envVars.ContainsKey("DATABASE_URL") -or $envVars.ContainsKey("SUPABASE_DB_URL") -or
    (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("DATABASE_URL"))) -or
    (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("SUPABASE_DB_URL"))))

if (-not $hasDbUrl) {
    $missing += "DATABASE_URL (or SUPABASE_DB_URL)"
}

Write-Host ""
if ($missing.Count -gt 0) {
    Write-Host "ENVIRONMENT CHECK FAILED:" -ForegroundColor Red
    foreach ($item in $missing) {
        Write-Host "  Missing required development environment variable: $item" -ForegroundColor Red
    }
    Write-Host "`nInstructions:" -ForegroundColor Yellow
    Write-Host "  1. Copy .env.example to .env:  Copy-Item .env.example .env" -ForegroundColor Yellow
    Write-Host "  2. Populate required development credentials securely (from team password manager)." -ForegroundColor Yellow
    Write-Host "  3. Never commit .env or secrets to git." -ForegroundColor Yellow
    Exit 1
} else {
    Write-Host "SUCCESS: Environment configured." -ForegroundColor Green
    Write-Host "All required development configuration variable names are set." -ForegroundColor Green
    Exit 0
}
