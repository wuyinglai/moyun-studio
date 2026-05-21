# solo-check.ps1 — Solo 代码质量检查脚本 (PowerShell)
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode docs
#   powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode backend
#   powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode frontend
#   powershell -ExecutionPolicy Bypass -File scripts/solo-check.ps1 -Mode all

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("docs", "backend", "frontend", "all")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$HasError = $false

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

# ---- Mode: docs ----
if ($Mode -eq "docs" -or $Mode -eq "all") {
    Run-Step "git diff --check" "git diff --check"
}

# ---- Mode: backend ----
if ($Mode -eq "backend" -or $Mode -eq "all") {
    $backendFiles = @(
        "backend/main.py",
        "backend/api/files.py",
        "backend/api/pipeline.py",
        "backend/api/generate.py",
        "backend/api/lite.py",
        "backend/api/candidates.py",
        "backend/core/file_ops.py",
        "backend/core/generation_service.py",
        "backend/core/pipeline.py",
        "backend/core/candidate_service.py",
        "backend/schemas/file.py"
    )

    $pyCompileCmd = ($backendFiles | ForEach-Object { "python -m py_compile $_" }) -join " && "
    Run-Step "py_compile backend files" $pyCompileCmd

    Run-Step "pytest backend" "python -m pytest backend/tests -q --tb=short"
}

# ---- Mode: frontend ----
if ($Mode -eq "frontend" -or $Mode -eq "all") {
    Push-Location (Join-Path $RootDir "frontend")
    try {
        Run-Step "npm run lint" "npm run lint"
        Run-Step "npm run build" "npm run build"
        Run-Step "npm run test:e2e:mock" "npm run test:e2e:mock"
    } finally {
        Pop-Location
    }
}

Write-Host ""
if ($HasError) {
    Write-Host "Some checks FAILED." -ForegroundColor Red
    exit 1
} else {
    Write-Host "All checks PASSED." -ForegroundColor Green
    exit 0
}
