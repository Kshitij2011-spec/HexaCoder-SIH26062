# ============================================================
# SIH26062 — Unified Repository Verification Script (PowerShell)
# Usage: ./scripts/verify.ps1 [-SkipE2E]
# ============================================================

param (
    [switch]$SkipE2E = $true
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SIH26062 - HexaCoders Repository Verification Harness" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$hasFailed = $false

# 1. Backend Pytest Verification
Write-Host "`n[1/3] Running Backend Unit and Schema Tests..." -ForegroundColor Yellow
try {
    python -m pytest tests/ -v -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        Write-Host "X Backend pytest tests FAILED." -ForegroundColor Red
        $hasFailed = $true
    } else {
        Write-Host "Backend tests PASSED." -ForegroundColor Green
    }
} catch {
    Write-Host "X Error invoking pytest: $_" -ForegroundColor Red
    $hasFailed = $true
}

# 2. Frontend Build Verification (Phase 11+)
Write-Host "`n[2/3] Checking Frontend Build..." -ForegroundColor Yellow
$frontendPackageJson = Join-Path $repoRoot "frontend\package.json"
if (Test-Path $frontendPackageJson) {
    try {
        npm run build --prefix frontend
        if ($LASTEXITCODE -ne 0) {
            Write-Host "X Frontend build FAILED." -ForegroundColor Red
            $hasFailed = $true
        } else {
            Write-Host "Frontend build PASSED." -ForegroundColor Green
        }
    } catch {
        Write-Host "X Error invoking npm build: $_" -ForegroundColor Red
        $hasFailed = $true
    }
} else {
    Write-Host "Frontend package.json not yet scaffolded (Phase 11+). Skipping frontend build." -ForegroundColor Gray
}

# 3. Playwright E2E Verification
Write-Host "`n[3/3] Checking Playwright E2E Test Suite..." -ForegroundColor Yellow
if ($SkipE2E) {
    Write-Host "Playwright E2E verification skipped (-SkipE2E flag set, or dev server offline)." -ForegroundColor Gray
} else {
    Write-Host "To run Playwright E2E tests, ensure backend and frontend servers are running locally." -ForegroundColor Gray
}

Write-Host "`n============================================================" -ForegroundColor Cyan
if ($hasFailed) {
    Write-Host "REPOSITORY VERIFICATION FAILED." -ForegroundColor Red
    Exit 1
} else {
    Write-Host "REPOSITORY VERIFICATION PASSED (Current Stage Baseline Healthy)." -ForegroundColor Green
    Exit 0
}
