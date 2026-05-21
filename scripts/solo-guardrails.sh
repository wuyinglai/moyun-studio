#!/usr/bin/env bash
# solo-guardrails.sh — Solo 安全围栏检查脚本 (Bash)
# 用法：
#   ./scripts/solo-guardrails.sh
#
# 检查规则：
#   1. backend/api 中直接 project_dir / req 或 project_dir / path 拼接
#   2. file.updated 携带 content
#   3. localStorage 保存 API Key
#   4. 前端文案残留：写下一部分、生成本节、重写本节、本节、下一节、批量生成章节
#   5. frontend/src 主动发送 output_mode overwrite
#   6. candidate source_path 出现 project_id/project_id

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HAS_HIT=0

check_pattern() {
    local rule_name="$1"
    local pattern="$2"
    local path="$3"
    local description="$4"

    local hits
    hits=$(grep -rn "$pattern" "$path" 2>/dev/null | grep -v "AI_GUARDRAIL_ALLOW" || true)

    if [[ -n "$hits" ]]; then
        echo ""
        echo "RULE: $rule_name"
        echo "  $description"
        while IFS= read -r line; do
            local rel_path="${line#$ROOT_DIR/}"
            echo "  HIT: $rel_path"
        done <<< "$hits"
        HAS_HIT=1
    fi
}

echo "=== Solo Guardrails Check ==="

# Rule 1: backend/api 中直接路径拼接
check_pattern "path-concat" "project_dir\s*/\s*\(req\|path\)" "$ROOT_DIR/backend/api/" "backend/api 中禁止直接 project_dir / req.path 拼接，必须走 FileService"

# Rule 2: file.updated 携带 content
check_pattern "file-updated-content" "file\.updated.*content" "$ROOT_DIR/backend/" "file.updated / SSE 事件不得携带完整正文 content"

# Rule 3: localStorage API Key
check_pattern "apikey-localstorage" "localStorage.*[Aa][Pp][Ii]\s*[Kk]ey" "$ROOT_DIR/frontend/src/" "API Key 不得写入 localStorage"

# Rule 4: 前端文案残留
for term in "写下一部分" "生成本节" "重写本节" "批量生成章节"; do
    check_pattern "terminology-residue" "$term" "$ROOT_DIR/frontend/src/" "前端文案残留禁用术语: $term"
done

# Rule 5: frontend/src 主动发送 output_mode overwrite
check_pattern "overwrite-frontend" "output_mode.*overwrite" "$ROOT_DIR/frontend/src/" "前端不应主动发送 output_mode=overwrite，应使用 write_scene/candidate/append"

# Rule 6: candidate source_path 重复 project_id
check_pattern "source-path-dup" "source_path.*project_id.*project_id" "$ROOT_DIR/backend/" "candidate source_path 不得出现 project_id/project_id 重复路径"

echo ""
if [[ $HAS_HIT -eq 0 ]]; then
    echo "All guardrails passed."
else
    echo "Guardrails check found issues." >&2
fi
exit $HAS_HIT
