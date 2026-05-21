#!/usr/bin/env bash
# ai-check.sh — Run quality checks for moyun-studio
# Usage: bash scripts/ai-check.sh [--backend|--frontend|--docs|--all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RUN_BACKEND=false
RUN_FRONTEND=false
RUN_DOCS=false

if [ $# -eq 0 ]; then
    echo "Usage: bash scripts/ai-check.sh [--backend|--frontend|--docs|--all]"
    exit 1
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --backend)  RUN_BACKEND=true ;;
        --frontend) RUN_FRONTEND=true ;;
        --docs)     RUN_DOCS=true ;;
        --all)      RUN_BACKEND=true; RUN_FRONTEND=true; RUN_DOCS=true ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash scripts/ai-check.sh [--backend|--frontend|--docs|--all]"
            exit 1
            ;;
    esac
    shift
done

OVERALL_PASS=true

# ── Backend ──────────────────────────────────────────────────────────
if [ "$RUN_BACKEND" = true ]; then
    echo ""
    echo "========================================"
    echo "  BACKEND CHECKS"
    echo "========================================"

    BACKEND_PASS=true

    echo ""
    echo "--- py_compile ---"
    COMPILE_FILES=(
        "backend/main.py"
        "backend/api/files.py"
        "backend/core/file_ops.py"
        "backend/core/generation_service.py"
        "backend/core/pipeline.py"
        "backend/core/candidate_service.py"
        "backend/schemas/file.py"
    )

    for f in "${COMPILE_FILES[@]}"; do
        if [ -f "$PROJECT_ROOT/$f" ]; then
            if python -m py_compile "$PROJECT_ROOT/$f" 2>&1; then
                echo "  PASS: $f"
            else
                echo "  FAIL: $f"
                BACKEND_PASS=false
            fi
        else
            echo "  SKIP: $f (not found)"
        fi
    done

    echo ""
    echo "--- pytest ---"
    if [ -d "$PROJECT_ROOT/backend/tests" ]; then
        if python -m pytest backend/tests -q --tb=short 2>&1; then
            echo "  PASS: pytest"
        else
            echo "  FAIL: pytest"
            BACKEND_PASS=false
        fi
    else
        echo "  SKIP: backend/tests not found"
    fi

    if [ "$BACKEND_PASS" = true ]; then
        echo ""
        echo "BACKEND: PASS"
    else
        echo ""
        echo "BACKEND: FAIL"
        OVERALL_PASS=false
    fi
fi

# ── Frontend ─────────────────────────────────────────────────────────
if [ "$RUN_FRONTEND" = true ]; then
    echo ""
    echo "========================================"
    echo "  FRONTEND CHECKS"
    echo "========================================"

    FRONTEND_PASS=true

    echo ""
    echo "--- lint ---"
    if (cd "$PROJECT_ROOT/frontend" && npm run lint 2>&1); then
        echo "  PASS: lint"
    else
        echo "  FAIL: lint"
        FRONTEND_PASS=false
    fi

    echo ""
    echo "--- build ---"
    if (cd "$PROJECT_ROOT/frontend" && npm run build 2>&1); then
        echo "  PASS: build"
    else
        echo "  FAIL: build"
        FRONTEND_PASS=false
    fi

    echo ""
    echo "--- test:e2e:mock ---"
    # Check if test:e2e:mock script exists in package.json
    if (cd "$PROJECT_ROOT/frontend" && node -e "const p=require('./package.json'); process.exit(p.scripts['test:e2e:mock'] ? 0 : 1)" 2>/dev/null); then
        if (cd "$PROJECT_ROOT/frontend" && npm run test:e2e:mock 2>&1); then
            echo "  PASS: test:e2e:mock"
        else
            echo "  FAIL: test:e2e:mock"
            FRONTEND_PASS=false
        fi
    else
        echo "  SKIP: npm run test:e2e:mock is not available. Please add it or run npm run test:e2e."
    fi

    if [ "$FRONTEND_PASS" = true ]; then
        echo ""
        echo "FRONTEND: PASS"
    else
        echo ""
        echo "FRONTEND: FAIL"
        OVERALL_PASS=false
    fi
fi

# ── Docs ─────────────────────────────────────────────────────────────
if [ "$RUN_DOCS" = true ]; then
    echo ""
    echo "========================================"
    echo "  DOCS CHECKS"
    echo "========================================"

    DOCS_PASS=true

    echo ""
    echo "--- git diff --check ---"
    if (cd "$PROJECT_ROOT" && git diff --check 2>&1); then
        echo "  PASS: no whitespace errors"
    else
        echo "  FAIL: whitespace errors detected"
        DOCS_PASS=false
    fi

    if [ "$DOCS_PASS" = true ]; then
        echo ""
        echo "DOCS: PASS"
    else
        echo ""
        echo "DOCS: FAIL"
        OVERALL_PASS=false
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  SUMMARY"
echo "========================================"

if [ "$OVERALL_PASS" = true ]; then
    echo "ALL CHECKS: PASS"
    exit 0
else
    echo "ALL CHECKS: FAIL"
    exit 1
fi
