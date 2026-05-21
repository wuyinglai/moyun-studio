# solo-guardrails.ps1 — Solo 安全围栏检查脚本 (PowerShell)
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts/solo-guardrails.ps1
#
# 检查规则：
#   1. backend/api 中直接 project_dir / req 或 project_dir / path 拼接
#   2. file.updated 携带 content
#   3. localStorage 保存 API Key
#   4. 前端文案残留：写下一部分、生成本节、重写本节、本节、下一节、批量生成章节
#   5. frontend/src 主动发送 output_mode overwrite
#   6. candidate source_path 出现 project_id/project_id

$ErrorActionPreference = "Continue"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$HasHit = $false

function Check-Pattern($ruleName, $pattern, $path, $description) {
    $hits = @()
    try {
        $hits = Select-String -Path $path -Pattern $pattern -CaseSensitive:$false | Where-Object {
            $_.Line -notmatch "AI_GUARDRAIL_ALLOW"
        }
    } catch {
        # 忽略无匹配文件
    }

    if ($hits.Count -gt 0) {
        Write-Host ""
        Write-Host "RULE: $ruleName" -ForegroundColor Yellow
        Write-Host "  $description" -ForegroundColor Yellow
        foreach ($hit in $hits) {
            $relPath = $hit.Path.Replace("$RootDir\", "")
            Write-Host "  HIT: ${relPath}:$($hit.LineNumber): $($hit.Line.Trim())" -ForegroundColor Red
        }
        $script:HasHit = $true
    }
}

Write-Host "=== Solo Guardrails Check ===" -ForegroundColor Cyan

# Rule 1: backend/api 中直接路径拼接
Check-Pattern `
    "path-concat" `
    "project_dir\s*/\s*(req|path)" `
    (Join-Path $RootDir "backend\api\*.py") `
    "backend/api 中禁止直接 project_dir / req.path 拼接，必须走 FileService"

# Rule 2: file.updated 携带 content
Check-Pattern `
    "file-updated-content" `
    "file\.updated.*content" `
    (Join-Path $RootDir "backend\**\*.py") `
    "file.updated / SSE 事件不得携带完整正文 content"

# Rule 3: localStorage API Key
Check-Pattern `
    "apikey-localstorage" `
    "localStorage.*[Aa][Pp][Ii]\s*[Kk]ey" `
    (Join-Path $RootDir "frontend\src\**\*.ts") `
    "API Key 不得写入 localStorage"

Check-Pattern `
    "apikey-localstorage-vue" `
    "localStorage.*[Aa][Pp][Ii]\s*[Kk]ey" `
    (Join-Path $RootDir "frontend\src\**\*.vue") `
    "API Key 不得写入 localStorage"

# Rule 4: 前端文案残留
$forbiddenTerms = @("写下一部分", "生成本节", "重写本节", "批量生成章节")
foreach ($term in $forbiddenTerms) {
    Check-Pattern `
        "terminology-residue" `
        $term `
        (Join-Path $RootDir "frontend\src\**\*.vue") `
        "前端文案残留禁用术语: $term"

    Check-Pattern `
        "terminology-residue-ts" `
        $term `
        (Join-Path $RootDir "frontend\src\**\*.ts") `
        "前端文案残留禁用术语: $term"
}

# Rule 5: frontend/src 主动发送 output_mode overwrite
Check-Pattern `
    "overwrite-frontend" `
    "output_mode.*overwrite" `
    (Join-Path $RootDir "frontend\src\**\*.ts") `
    "前端不应主动发送 output_mode=overwrite，应使用 write_scene/candidate/append"

Check-Pattern `
    "overwrite-frontend-vue" `
    "output_mode.*overwrite" `
    (Join-Path $RootDir "frontend\src\**\*.vue") `
    "前端不应主动发送 output_mode=overwrite，应使用 write_scene/candidate/append"

# Rule 6: candidate source_path 重复 project_id
Check-Pattern `
    "source-path-dup" `
    "source_path.*project_id.*project_id" `
    (Join-Path $RootDir "backend\**\*.py") `
    "candidate source_path 不得出现 project_id/project_id 重复路径"

Write-Host ""
if ($HasHit) {
    Write-Host "Guardrails check found issues." -ForegroundColor Red
    exit 1
} else {
    Write-Host "All guardrails passed." -ForegroundColor Green
    exit 0
}
