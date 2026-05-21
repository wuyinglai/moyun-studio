# ai-check.ps1 — Run quality checks for moyun-studio (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/ai-check.ps1 -Mode backend|frontend|docs|all

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("backend", "frontend", "docs", "all")]
    [string]$Mode
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

$RunBackend  = ($Mode -eq "backend" -or $Mode -eq "all")
$RunFrontend = ($Mode -eq "frontend" -or $Mode -eq "all")
$RunDocs     = ($Mode -eq "docs" -or $Mode -eq "all")

$OverallPass = $true

# ── Backend ──────────────────────────────────────────────────────────
if ($RunBackend) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  BACKEND CHECKS"
    Write-Host "========================================"

    $BackendPass = $true

    Write-Host ""
    Write-Host "--- py_compile ---"
    $CompileFiles = @(
        "backend/main.py",
        "backend/api/files.py",
        "backend/core/file_ops.py",
        "backend/core/generation_service.py",
        "backend/core/pipeline.py",
        "backend/core/candidate_service.py",
        "backend/schemas/file.py"
    )

    foreach ($f in $CompileFiles) {
        $fullPath = Join-Path $ProjectRoot $f
        if (Test-Path $fullPath) {
            $result = & python -m py_compile $fullPath 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  PASS: $f"
            } else {
                Write-Host "  FAIL: $f"
                Write-Host $result
                $BackendPass = $false
            }
        } else {
            Write-Host "  SKIP: $f (not found)"
        }
    }

    Write-Host ""
    Write-Host "--- pytest ---"
    $testsDir = Join-Path $ProjectRoot "backend/tests"
    if (Test-Path $testsDir) {
        Push-Location $ProjectRoot
        & python -m pytest backend/tests -q --tb=short 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  PASS: pytest"
        } else {
            Write-Host "  FAIL: pytest"
            $BackendPass = $false
        }
        Pop-Location
    } else {
        Write-Host "  SKIP: backend/tests not found"
    }

    Write-Host ""
    if ($BackendPass) {
        Write-Host "BACKEND: PASS"
    } else {
        Write-Host "BACKEND: FAIL"
        $OverallPass = $false
    }
}

# ── Frontend ─────────────────────────────────────────────────────────
if ($RunFrontend) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  FRONTEND CHECKS"
    Write-Host "========================================"

    $FrontendPass = $true
    $FrontendDir = Join-Path $ProjectRoot "frontend"

    Write-Host ""
    Write-Host "--- lint ---"
    Push-Location $FrontendDir
    & npm run lint 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS: lint"
    } else {
        Write-Host "  FAIL: lint"
        $FrontendPass = $false
    }

    Write-Host ""
    Write-Host "--- build ---"
    & npm run build 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS: build"
    } else {
        Write-Host "  FAIL: build"
        $FrontendPass = $false
    }

    Write-Host ""
    Write-Host "--- test:e2e:mock ---"
    $packageJson = Get-Content (Join-Path $FrontendDir "package.json") -Raw | ConvertFrom-Json
    $hasE2eMock = $packageJson.scripts.PSObject.Properties.Name -contains "test:e2e:mock"
    if ($hasE2eMock) {
        & npm run test:e2e:mock 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  PASS: test:e2e:mock"
        } else {
            Write-Host "  FAIL: test:e2e:mock"
            $FrontendPass = $false
        }
    } else {
        Write-Host "  SKIP: npm run test:e2e:mock is not available. Please add it or run npm run test:e2e."
    }
    Pop-Location

    Write-Host ""
    if ($FrontendPass) {
        Write-Host "FRONTEND: PASS"
    } else {
        Write-Host "FRONTEND: FAIL"
        $OverallPass = $false
    }
}

# ── Docs ─────────────────────────────────────────────────────────────
if ($RunDocs) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  DOCS CHECKS"
    Write-Host "========================================"

    $DocsPass = $true

    Write-Host ""
    Write-Host "--- git diff --check ---"
    Push-Location $ProjectRoot
    & git diff --check 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS: no whitespace errors"
    } else {
        Write-Host "  FAIL: whitespace errors detected"
        $DocsPass = $false
    }
    Pop-Location

    Write-Host ""
    if ($DocsPass) {
        Write-Host "DOCS: PASS"
    } else {
        Write-Host "DOCS: FAIL"
        $OverallPass = $false
    }
}

# ── Summary ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================"
Write-Host "  SUMMARY"
Write-Host "========================================"

if ($OverallPass) {
    Write-Host "ALL CHECKS: PASS"
    exit 0
} else {
    Write-Host "ALL CHECKS: FAIL"
    exit 1
}
