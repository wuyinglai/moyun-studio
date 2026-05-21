# release-check.ps1 — v0.1.0 Release Check (PowerShell)
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts/release-check.ps1
#
# 此脚本不运行真实 LLM E2E 测试，不需要 API Key。
# 真实 LLM E2E 是单独的可选检查，需要设置环境变量 MOYUN_E2E_REAL_LLM=true。

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

Write-Host "=== Moyun Studio v0.1.0 Release Check ===" -ForegroundColor Yellow
Write-Host "NOTE: Real LLM E2E is intentionally skipped." -ForegroundColor Yellow
Write-Host "      To run real LLM E2E, set MOYUN_E2E_REAL_LLM=true separately." -ForegroundColor Yellow

# ---- 1. Git whitespace check ----
Run-Step "git diff --check" "git diff --check"

# ---- 2. Guardrails ----
Run-Step "Solo Guardrails" "powershell -ExecutionPolicy Bypass -File `"$RootDir\scripts\solo-guardrails.ps1`""

# ---- 3. Backend safety tests (A-E) ----
$safetyTests = @(
    "backend/tests/test_generation_output_policy.py",
    "backend/tests/test_pipeline.py",
    "backend/tests/test_lite_path_safety.py",
    "backend/tests/test_story_state.py",
    "backend/tests/test_style_guide.py",
    "backend/tests/test_recent_context.py",
    "backend/tests/test_workflow_memory.py",
    "backend/tests/test_materials.py",
    "backend/tests/test_llm.py"
) -join " "

Run-Step "Backend Safety Tests (A-E)" "python -m pytest $safetyTests -q --tb=short --timeout=60"

# ---- 4. Full backend tests ----
Run-Step "Full Backend Tests" "python -m pytest backend/tests -q --tb=short --timeout=60"

# ---- 5. Frontend lint & build ----
$frontendDir = Join-Path $RootDir "frontend"
if (Test-Path (Join-Path $frontendDir "node_modules")) {
    Push-Location $frontendDir
    try {
        Run-Step "Frontend Lint" "npm run lint"
        Run-Step "Frontend Build" "npm run build"
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "=== Frontend Checks ===" -ForegroundColor Cyan
    Write-Host "SKIPPED: frontend/node_modules not found. Run 'cd frontend && npm install' first." -ForegroundColor Yellow
}

# ---- 6. Mock E2E ----
if (Test-Path (Join-Path $frontendDir "node_modules")) {
    Push-Location $frontendDir
    try {
        $mockScript = Get-ChildItem -Path "tests" -Recurse -Filter "*mock*" -ErrorAction SilentlyContinue
        if ($mockScript) {
            Run-Step "Mock E2E" "npm run test:e2e:mock"
        } else {
            Write-Host "SKIPPED: No mock E2E script found." -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "SKIPPED: Mock E2E (no node_modules)." -ForegroundColor Yellow
}

# ---- Summary ----
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($HasError) {
    Write-Host "Release check FAILED. Fix issues before release." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Release check PASSED. Ready for v0.1.0." -ForegroundColor Green
    exit 0
}
