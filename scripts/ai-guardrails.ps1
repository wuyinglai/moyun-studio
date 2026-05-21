# ai-guardrails.ps1 — Check for common dangerous AI edits in moyun-studio (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/ai-guardrails.ps1

$ErrorActionPreference = "Continue"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

$FoundIssues = $false

function Check-Rule {
    param(
        [string]$RuleName,
        [string]$SearchPath,
        [string]$Pattern,
        [string]$Description
    )

    Write-Host ""
    Write-Host "--- Rule: $RuleName ---"
    Write-Host "  Description: $Description"
    Write-Host "  Searching: $SearchPath for: $Pattern"

    $fullSearchPath = Join-Path $ProjectRoot $SearchPath
    if (-not (Test-Path $fullSearchPath)) {
        Write-Host "  SKIP: $SearchPath does not exist"
        return
    }

    $ruleHits = @()
    try {
        $files = Get-ChildItem -Path $fullSearchPath -Recurse -File -ErrorAction SilentlyContinue -Exclude *.pyc | Where-Object {
            $_.FullName -notmatch '__pycache__|\\venv\\|\\.venv\\|\\node_modules\\'
        }
        foreach ($file in $files) {
            try {
                $lines = Select-String -Path $file.FullName -Pattern $Pattern -ErrorAction SilentlyContinue
                foreach ($line in $lines) {
                    $relativePath = $file.FullName.Substring($ProjectRoot.Path.Length + 1)
                    $lineText = if ($line.Line -is [string]) { $line.Line.Trim() } else { $line.Line.ToString().Trim() }
                    $ruleHits += "${relativePath}:$($line.LineNumber): ${lineText}"
                }
            } catch {
                # Skip files that cannot be searched (binary, locked, etc.)
            }
        }
    } catch {
        Write-Host "  SKIP: error searching $SearchPath"
        return
    }

    if ($ruleHits.Count -eq 0) {
        Write-Host "  PASS: no violations found"
        return
    }

    # Filter out lines with AI_GUARDRAIL_ALLOW whitelist
    $filtered = @()
    foreach ($m in $ruleHits) {
        if ($m -match "AI_GUARDRAIL_ALLOW") {
            Write-Host "  ALLOWLISTED: $m"
        } else {
            $filtered += $m
        }
    }

    if ($filtered.Count -gt 0) {
        Write-Host "  VIOLATION FOUND:"
        foreach ($f in $filtered) {
            Write-Host "    $f"
        }
        $script:FoundIssues = $true
    } else {
        Write-Host "  PASS: all hits were allowlisted"
    }
}

Write-Host "========================================"
Write-Host "  AI GUARDRAILS CHECK"
Write-Host "========================================"

# Rule 1: Backend API layer must not directly concatenate paths
Check-Rule `
    -RuleName "API path concatenation" `
    -SearchPath "backend/api" `
    -Pattern 'project_dir / req|project_dir / path|workspace / req' `
    -Description "Backend API layer must not use project_dir / req or workspace / req directly. Use FileService instead."

# Rule 2: file.updated must not send content
Check-Rule `
    -RuleName "file.updated content leak" `
    -SearchPath "backend" `
    -Pattern 'file\.updated|"content": req\.content|"content": content' `
    -Description "file.updated SSE event must not carry full content. Check event_bus.py and SSE endpoints."

# Rule 3: Frontend must not store API Key in localStorage
Check-Rule `
    -RuleName "API Key in localStorage" `
    -SearchPath "frontend/src" `
    -Pattern 'localStorage.*apiKey|localStorage.*api_key|localStorage.*API_KEY|apiKey.*localStorage|api_key.*localStorage|API_KEY.*localStorage' `
    -Description "API Key must not be written to localStorage."

# Rule 4: Scene UI must not misuse '节' (section)
Check-Rule `
    -RuleName "Scene terminology (节)" `
    -SearchPath "frontend/src" `
    -Pattern '重写这一节|下一节|本节|节内容|批量生成章节' `
    -Description "Scene-related UI must use '场景' not '节'. sec = scene, not section."

Check-Rule `
    -RuleName "Scene terminology in docs (节)" `
    -SearchPath "docs" `
    -Pattern '重写这一节|下一节|本节|节内容|批量生成章节' `
    -Description "Documentation must use '场景' not '节' for scene references."

# Rule 5: candidate.source_path must not contain duplicate project_id
Check-Rule `
    -RuleName "Duplicate project_id in source_path" `
    -SearchPath "backend" `
    -Pattern 'source_path=.*project_id|project_id/project_id' `
    -Description "candidate.source_path must be a relative path within the project, must not contain duplicate project_id."

# Rule 6: output_mode overwrite requires human confirmation
Check-Rule `
    -RuleName "output_mode overwrite" `
    -SearchPath "backend" `
    -Pattern 'output_mode.*overwrite' `
    -Description "output_mode=overwrite is dangerous. Ensure human confirmation is required before applying."

# ── Summary ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================"
Write-Host "  GUARDRAILS SUMMARY"
Write-Host "========================================"

if ($FoundIssues) {
    Write-Host "GUARDRAILS: FAIL — dangerous patterns found"
    Write-Host ""
    Write-Host "If a hit is a documentation example of a forbidden pattern,"
    Write-Host "add AI_GUARDRAIL_ALLOW on the same line to allowlist it."
    exit 1
} else {
    Write-Host "GUARDRAILS: PASS"
    exit 0
}
