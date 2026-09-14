# =============================================================================
# The Lenny Growth Assistant -- Consolidated Test Runner (PowerShell)
# Runs both Backend Pytest and Frontend Vitest suites with summary reporting.
# =============================================================================

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  The Lenny Growth Assistant -- Consolidated Test Runner" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$BackendPassed = $false
$FrontendPassed = $false
$StartTime = Get-Date

# ---------------------------------------------------------------------------
# 1. Backend Pytest Suite
# ---------------------------------------------------------------------------
Write-Host "[1/2] Running Backend Pytest Suite..." -ForegroundColor Yellow
$PytestCmd = if (Test-Path "$RepoRoot\.venv\Scripts\pytest.exe") {
    "$RepoRoot\.venv\Scripts\pytest.exe"
} else {
    "pytest"
}

& $PytestCmd -v
if ($LASTEXITCODE -eq 0) {
    $BackendPassed = $true
    Write-Host "  --> Backend tests PASSED." -ForegroundColor Green
} else {
    Write-Host "  --> Backend tests FAILED." -ForegroundColor Red
}

Write-Host ""

# ---------------------------------------------------------------------------
# 2. Frontend Vitest / RTL Suite
# ---------------------------------------------------------------------------
Write-Host "[2/2] Running Frontend Vitest / RTL Suite..." -ForegroundColor Yellow
Push-Location "$RepoRoot\frontend"

$NpmCmd = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { "npm.cmd" } else { "npm" }
& $NpmCmd test -- --run

if ($LASTEXITCODE -eq 0) {
    $FrontendPassed = $true
    Write-Host "  --> Frontend tests PASSED." -ForegroundColor Green
} else {
    Write-Host "  --> Frontend tests FAILED." -ForegroundColor Red
}

Pop-Location

Write-Host ""
$EndTime = Get-Date
$Duration = [math]::Round(($EndTime - $StartTime).TotalSeconds, 2)

# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------
$BackendStatus = if ($BackendPassed) { "PASSED" } else { "FAILED" }
$BackendColor = if ($BackendPassed) { "Green" } else { "Red" }
$FrontendStatus = if ($FrontendPassed) { "PASSED" } else { "FAILED" }
$FrontendColor = if ($FrontendPassed) { "Green" } else { "Red" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "                    TEST EXECUTION SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Backend Suite (Pytest)     : $BackendStatus" -ForegroundColor $BackendColor
Write-Host "  Frontend Suite (Vitest/RTL): $FrontendStatus" -ForegroundColor $FrontendColor
Write-Host "  Total Duration             : $Duration seconds" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

if ($BackendPassed -and $FrontendPassed) {
    Write-Host "SUCCESS: All test suites passed cleanly with 0 errors." -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAILURE: One or more test suites failed." -ForegroundColor Red
    exit 1
}
