#!/usr/bin/env bash
# ai-guardrails.sh — Check for common dangerous AI edits in moyun-studio
# Usage: bash scripts/ai-guardrails.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

FOUND_ISSUES=false

check_rule() {
    local rule_name="$1"
    local search_path="$2"
    local pattern="$3"
    local description="$4"

    echo ""
    echo "--- Rule: $rule_name ---"
    echo "  Description: $description"
    echo "  Searching: $search_path for: $pattern"

    if [ ! -d "$PROJECT_ROOT/$search_path" ] && [ ! -f "$PROJECT_ROOT/$search_path" ]; then
        echo "  SKIP: $search_path does not exist"
        return
    fi

    local matches
    matches=$(cd "$PROJECT_ROOT" && grep -rn --exclude-dir='__pycache__' --exclude-dir='venv' --exclude-dir='.venv' --exclude-dir='node_modules' "$pattern" "$search_path" 2>/dev/null || true)

    if [ -z "$matches" ]; then
        echo "  PASS: no violations found"
        return
    fi

    # Filter out lines with AI_GUARDRAIL_ALLOW whitelist
    local filtered=""
    while IFS= read -r line; do
        if echo "$line" | grep -q "AI_GUARDRAIL_ALLOW"; then
            echo "  ALLOWLISTED: $line"
        else
            if [ -z "$filtered" ]; then
                filtered="$line"
            else
                filtered="$filtered"$'\n'"$line"
            fi
        fi
    done <<< "$matches"

    if [ -n "$filtered" ]; then
        echo "  VIOLATION FOUND:"
        echo "$filtered" | while IFS= read -r line; do
            echo "    $line"
        done
        FOUND_ISSUES=true
    else
        echo "  PASS: all hits were allowlisted"
    fi
}

echo "========================================"
echo "  AI GUARDRAILS CHECK"
echo "========================================"

# Rule 1: Backend API layer must not directly concatenate paths
check_rule \
    "API path concatenation" \
    "backend/api" \
    'project_dir / req\|project_dir / path\|workspace / req' \
    "Backend API layer must not use project_dir / req or workspace / req directly. Use FileService instead."

# Rule 2: file.updated must not send content
check_rule \
    "file.updated content leak" \
    "backend" \
    'file\.updated\|"content": req\.content\|"content": content' \
    "file.updated SSE event must not carry full content. Check event_bus.py and SSE endpoints."

# Rule 3: Frontend must not store API Key in localStorage
check_rule \
    "API Key in localStorage" \
    "frontend/src" \
    'localStorage.*apiKey\|localStorage.*api_key\|localStorage.*API_KEY\|apiKey.*localStorage\|api_key.*localStorage\|API_KEY.*localStorage' \
    "API Key must not be written to localStorage."

# Rule 4: Scene UI must not misuse '节' (section)
check_rule \
    "Scene terminology (节)" \
    "frontend/src" \
    '重写这一节\|下一节\|本节\|节内容\|批量生成章节' \
    "Scene-related UI must use '场景' not '节'. sec = scene, not section."

# Also check docs for the same terminology issues
check_rule \
    "Scene terminology in docs (节)" \
    "docs" \
    '重写这一节\|下一节\|本节\|节内容\|批量生成章节' \
    "Documentation must use '场景' not '节' for scene references."

# Rule 5: candidate.source_path must not contain duplicate project_id
check_rule \
    "Duplicate project_id in source_path" \
    "backend" \
    'source_path=.*project_id\|project_id/project_id' \
    "candidate.source_path must be a relative path within the project, must not contain duplicate project_id."

# Rule 6: output_mode overwrite requires human confirmation
check_rule \
    "output_mode overwrite" \
    "backend" \
    'output_mode.*overwrite' \
    "output_mode=overwrite is dangerous. Ensure human confirmation is required before applying."

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  GUARDRAILS SUMMARY"
echo "========================================"

if [ "$FOUND_ISSUES" = true ]; then
    echo "GUARDRAILS: FAIL — dangerous patterns found"
    echo ""
    echo "If a hit is a documentation example of a forbidden pattern,"
    echo "add AI_GUARDRAIL_ALLOW on the same line to allowlist it."
    exit 1
else
    echo "GUARDRAILS: PASS"
    exit 0
fi
