#!/usr/bin/env bash
# solo-check.sh — Solo 代码质量检查脚本 (Bash)
# 用法：
#   ./scripts/solo-check.sh docs
#   ./scripts/solo-check.sh backend
#   ./scripts/solo-check.sh frontend
#   ./scripts/solo-check.sh all

set -euo pipefail

MODE="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HAS_ERROR=0

if [[ -z "$MODE" ]]; then
    echo "Usage: $0 <docs|backend|frontend|all>"
    exit 1
fi

run_step() {
    local name="$1"
    shift
    echo ""
    echo "=== $name ==="
    if "$@"; then
        echo "PASSED: $name"
    else
        echo "FAILED: $name (exit code $?)" >&2
        HAS_ERROR=1
    fi
}

# ---- Mode: docs ----
if [[ "$MODE" == "docs" || "$MODE" == "all" ]]; then
    run_step "git diff --check" git diff --check
fi

# ---- Mode: backend ----
if [[ "$MODE" == "backend" || "$MODE" == "all" ]]; then
    backend_files=(
        "backend/main.py"
        "backend/api/files.py"
        "backend/api/pipeline.py"
        "backend/api/generate.py"
        "backend/api/lite.py"
        "backend/api/candidates.py"
        "backend/core/file_ops.py"
        "backend/core/generation_service.py"
        "backend/core/pipeline.py"
        "backend/core/candidate_service.py"
        "backend/schemas/file.py"
    )

    compile_ok=true
    for f in "${backend_files[@]}"; do
        if ! python -m py_compile "$f" 2>/dev/null; then
            echo "  py_compile FAILED: $f"
            compile_ok=false
        fi
    done
    if $compile_ok; then
        echo "PASSED: py_compile backend files"
    else
        echo "FAILED: py_compile backend files"
        HAS_ERROR=1
    fi

    run_step "pytest backend" python -m pytest backend/tests -q --tb=short
fi

# ---- Mode: frontend ----
if [[ "$MODE" == "frontend" || "$MODE" == "all" ]]; then
    cd "$ROOT_DIR/frontend"
    run_step "npm run lint" npm run lint
    run_step "npm run build" npm run build
    run_step "npm run test:e2e:mock" npm run test:e2e:mock
fi

echo ""
if [[ $HAS_ERROR -eq 0 ]]; then
    echo "All checks PASSED."
else
    echo "Some checks FAILED." >&2
fi
exit $HAS_ERROR
