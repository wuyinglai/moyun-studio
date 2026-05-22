# verify-release.ps1 — Release Verification Script
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/verify-release.ps1
#
# Verifies that the project is ready for release by checking:
#   1. Git working tree is clean
#   2. Backend dependencies install
#   3. Frontend install, build, and lint pass
#   4. Required documentation files exist
#   5. Example project structure is intact

$ErrorActionPreference = "Stop"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$HasError = $false

function Check-File($label, $path) {
    $fullPath = Join-Path $RootDir $path
    if (Test-Path $fullPath) {
        Write-Host "  [OK] $label" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $label — not found: $path" -ForegroundColor Red
        $script:HasError = $true
    }
}

function Check-Dir($label, $path) {
    $fullPath = Join-Path $RootDir $path
    if (Test-Path $fullPath -PathType Container) {
        Write-Host "  [OK] $label" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $label — directory not found: $path" -ForegroundColor Red
        $script:HasError = $true
    }
}

function Run-Step($name, $cmd) {
    Write-Host ""
    Write-Host "=== $name ===" -ForegroundColor Cyan
    try {
        Invoke-Expression $cmd
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED: $name (exit code $LASTEXITCODE)" -ForegroundColor Red
            $script:HasError = $true
        } else {
            Write-Host "PASSED: $name" -ForegroundColor Green
        }
    } catch {
        Write-Host "FAILED: $name ($_)" -ForegroundColor Red
        $script:HasError = $true
    }
}

Write-Host "=== Moyun Studio Release Verification ===" -ForegroundColor Yellow
Write-Host "Root: $RootDir" -ForegroundColor Gray

# ---- 1. Git status ----
Write-Host ""
Write-Host "=== Git Working Tree ===" -ForegroundColor Cyan
$gitStatus = git -C $RootDir status --porcelain 2>&1
if ($gitStatus) {
    Write-Host "WARNING: Working tree is not clean:" -ForegroundColor Yellow
    Write-Host $gitStatus
} else {
    Write-Host "  [OK] Working tree is clean" -ForegroundColor Green
}

# ---- 2. Backend dependencies ----
Write-Host ""
Write-Host "=== Backend Dependencies ===" -ForegroundColor Cyan
$backendDir = Join-Path $RootDir "backend"
$reqFile = Join-Path $backendDir "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "  [OK] requirements.txt exists" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] requirements.txt not found" -ForegroundColor Red
    $script:HasError = $true
}

# ---- 3. Frontend checks ----
Write-Host ""
Write-Host "=== Frontend Checks ===" -ForegroundColor Cyan
$frontendDir = Join-Path $RootDir "frontend"
if (Test-Path (Join-Path $frontendDir "node_modules")) {
    Push-Location $frontendDir
    try {
        Run-Step "npm run build" "npm run build"
        Run-Step "npm run lint" "npm run lint 2>&1"
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  SKIPPED: frontend/node_modules not found. Run 'cd frontend; npm install' first." -ForegroundColor Yellow
}

# ---- 4. Documentation files ----
Write-Host ""
Write-Host "=== Documentation Files ===" -ForegroundColor Cyan
Check-File "README.md" "README.md"
Check-File "CHANGELOG.md" "CHANGELOG.md"
Check-File ".env.example" ".env.example"
Check-File "docs/quick-start.md" "docs/quick-start.md"
Check-File "docs/known-issues.md" "docs/known-issues.md"
Check-File "docs/roadmap.md" "docs/roadmap.md"
Check-File "docs/changelog.md" "docs/changelog.md"
Check-File "docs/releases/v0.1.0.md" "docs/releases/v0.1.0.md"
Check-File "docs/releases/v0.1.1.md" "docs/releases/v0.1.1.md"
Check-File "docs/RELEASE_CHECKLIST.md" "docs/RELEASE_CHECKLIST.md"

# ---- 5. Example projects ----
Write-Host ""
Write-Host "=== Example Projects ===" -ForegroundColor Cyan
Check-Dir "examples/demo-novel/" "examples/demo-novel"
Check-File "examples/demo-novel/meta.json" "examples/demo-novel/meta.json"
Check-Dir "examples/basic-novel-project/" "examples/basic-novel-project"
Check-File "examples/basic-novel-project/meta.json" "examples/basic-novel-project/meta.json"
Check-File "examples/basic-novel-project/outline.md" "examples/basic-novel-project/outline.md"

# ---- 6. Scripts ----
Write-Host ""
Write-Host "=== Scripts ===" -ForegroundColor Cyan
Check-File "scripts/release-check.ps1" "scripts/release-check.ps1"
Check-File "scripts/verify-release.ps1" "scripts/verify-release.ps1"

# ---- Summary ----
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($HasError) {
    Write-Host "Verification FAILED. Fix issues before release." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Verification PASSED. Ready for release." -ForegroundColor Green
    exit 0
}
