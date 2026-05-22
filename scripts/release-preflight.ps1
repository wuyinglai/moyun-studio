# release-preflight.ps1 — Release Preflight Checks
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1 -Version v0.2.0
#
# Checks that must pass before creating a release:
#   1. Current branch is main
#   2. Working tree is clean
#   3. Version tag does not exist locally
#   4. Version tag does not exist on origin
#   5. Release notes file exists
#   6. gh CLI is available (warning if not)

param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$HasError = $false
$HasWarning = $false

function Check-Pass($label) {
    Write-Host "  [PASS] $label" -ForegroundColor Green
}

function Check-Fail($label, $fix) {
    Write-Host "  [FAIL] $label" -ForegroundColor Red
    if ($fix) { Write-Host "         Fix: $fix" -ForegroundColor Yellow }
    $script:HasError = $true
}

function Check-Warn($label, $note) {
    Write-Host "  [WARN] $label" -ForegroundColor Yellow
    if ($note) { Write-Host "         Note: $note" -ForegroundColor Gray }
    $script:HasWarning = $true
}

Write-Host "=== Moyun Studio Release Preflight ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor White
Write-Host "Root:    $RootDir" -ForegroundColor Gray
Write-Host ""

# ---- 1. Current branch ----
Write-Host "=== Branch Check ===" -ForegroundColor Cyan
$currentBranch = git -C $RootDir rev-parse --abbrev-ref HEAD 2>&1
if ($currentBranch -eq "main") {
    Check-Pass "Current branch is 'main'"
} else {
    Check-Fail "Current branch is '$currentBranch', expected 'main'" "git checkout main"
}

# ---- 2. Clean working tree ----
Write-Host ""
Write-Host "=== Working Tree Check ===" -ForegroundColor Cyan
$gitStatus = git -C $RootDir status --porcelain 2>&1
if ($gitStatus) {
    Check-Fail "Working tree is not clean" "Commit or stash changes before release"
    Write-Host "         Uncommitted files:" -ForegroundColor Yellow
    $gitStatus | ForEach-Object { Write-Host "           $_" -ForegroundColor Gray }
} else {
    Check-Pass "Working tree is clean"
}

# ---- 3. Local tag does not exist ----
Write-Host ""
Write-Host "=== Local Tag Check ===" -ForegroundColor Cyan
$localTag = git -C $RootDir tag -l $Version 2>&1
if ($localTag) {
    $tagCommit = git -C $RootDir rev-parse "$Version^{commit}" 2>&1
    $headCommit = git -C $RootDir rev-parse HEAD 2>&1
    Check-Fail "Tag '$Version' already exists locally (points to $tagCommit)" "git tag -d $Version"
} else {
    Check-Pass "Tag '$Version' does not exist locally"
}

# ---- 4. Remote tag does not exist ----
Write-Host ""
Write-Host "=== Remote Tag Check ===" -ForegroundColor Cyan
try {
    $remoteTag = git -C $RootDir ls-remote --tags origin "refs/tags/$Version" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-remote failed"
    }
    if ($remoteTag) {
        Check-Fail "Tag '$Version' already exists on origin" "git push origin :refs/tags/$Version"
    } else {
        Check-Pass "Tag '$Version' does not exist on origin"
    }
} catch {
    Check-Warn "Cannot check remote tag (network error or no remote)" "Check connectivity and re-run; verify manually with: git ls-remote --tags origin $Version"
}

# ---- 5. Release notes file exists ----
Write-Host ""
Write-Host "=== Release Notes Check ===" -ForegroundColor Cyan
$releaseNotesPath = Join-Path $RootDir "docs/releases/$Version.md"
if (Test-Path $releaseNotesPath) {
    Check-Pass "Release notes exist: docs/releases/$Version.md"
} else {
    Check-Fail "Release notes not found: docs/releases/$Version.md" "Create the release notes file"
}

# ---- 6. gh CLI availability ----
Write-Host ""
Write-Host "=== GitHub CLI Check ===" -ForegroundColor Cyan
$ghAvailable = $false
try {
    $ghVersion = gh --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ghAvailable = $true
        Check-Pass "gh CLI is available ($($ghVersion.Split("`n")[0]))"
    }
} catch {
    # gh not found
}

if (-not $ghAvailable) {
    Check-Warn "gh CLI is not installed" "Install gh CLI or use Python fallback (see docs/release-preflight.md)"
}

# ---- Summary ----
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($HasError) {
    Write-Host "Preflight FAILED — fix errors before proceeding." -ForegroundColor Red
    Write-Host "See docs/release-preflight.md for help." -ForegroundColor Yellow
    exit 1
} elseif ($HasWarning) {
    Write-Host "Preflight PASSED with warnings." -ForegroundColor Yellow
    Write-Host "You may proceed, but review warnings above." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Preflight PASSED — ready to release $Version." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. git push origin main" -ForegroundColor Gray
    Write-Host "  2. git tag $Version" -ForegroundColor Gray
    Write-Host "  3. git push origin $Version" -ForegroundColor Gray
    Write-Host "  4. gh release create $Version --title 'Moyun Studio $Version' --notes-file docs/releases/$Version.md" -ForegroundColor Gray
    exit 0
}
