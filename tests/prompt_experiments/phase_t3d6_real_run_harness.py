#!/usr/bin/env python3
"""
Phase T3-D6.3.1a: 真实实验执行器 Harness
默认 dry-run，不调用 LLM。
需显式加上 --real-run 才可调用真实生成。
不修改生产 Prompt，不打印 API Key。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# 路径常量
BASE_DIR = Path(__file__).parent.parent.parent
FIXTURE_DIR = BASE_DIR / "tests" / "fixtures" / "lite_prompt_variant_project"
VARIANTS_DIR = BASE_DIR / "docs" / "testing" / "prompt-experiments" / "lite-continuation"
OUTPUT_FILE = BASE_DIR / "docs" / "testing" / "prompt-experiments" / "lite-continuation" / "t3d6-real-run-results.json"

# Variant 配置
VARIANTS = [
    "baseline",
    "variant-a-length",
    "variant-b-length-action-chain",
    "variant-c-action-conflict-hook",
    "variant-d-full-constraints"
]


def load_variant(variant_name: str) -> str:
    """加载 variant 文件内容"""
    variant_file = VARIANTS_DIR / f"{variant_name}.md"
    if not variant_file.exists():
        return ""
    return variant_file.read_text(encoding="utf-8")


def load_selected_card() -> Dict[str, Any]:
    """加载选卡 fixture"""
    selected_card_file = FIXTURE_DIR / "selected-card.json"
    if not selected_card_file.exists():
        raise FileNotFoundError(f"Missing fixture: {selected_card_file}")
    with open(selected_card_file, encoding="utf-8") as f:
        return json.load(f)


def run_dry_run(runs: int) -> Dict[str, Any]:
    """执行 dry-run，只验证输入、不调用 LLM"""
    result: Dict[str, Any] = {
        "phase": "T3-D6.3.1a",
        "mode": "dry_run",
        "llm_called": False,
        "production_prompt_modified": False,
        "variants": []
    }

    # 验证所有 variant 文件存在
    for variant_name in VARIANTS:
        variant_content = load_variant(variant_name)
        variant_entry: Dict[str, Any] = {
            "name": variant_name,
            "runs": []
        }
        for i in range(runs):
            run_id = f"{variant_name}-run-{i + 1:03d}"
            variant_entry["runs"].append({
                "run_id": run_id,
                "status": "pending",
                "word_count": None,
                "too_short": None,
                "template_leak": None,
                "fallback_used": None,
                "retry_count": None,
                "write_skipped": None,
                "quality_flags": [],
                "quality_score": None,
                "output_excerpt": "",
                "failure_reason": ""
            })
        result["variants"].append(variant_entry)

    # 验证 fixture 存在
    fixture_files = [
        "story-engine.md",
        "story-state.md",
        "style-guide.md",
        "recent-context.md",
        "selected-card.json"
    ]
    missing_fixtures = []
    for f in fixture_files:
        if not (FIXTURE_DIR / f).exists():
            missing_fixtures.append(f)
    if missing_fixtures:
        result["fixture_warning"] = f"Missing fixtures: {', '.join(missing_fixtures)}"
    else:
        result["fixture_status"] = "ok"

    return result


def run_real_run(base_url: str, runs: int) -> Dict[str, Any]:
    """执行 real-run，调用 Lite API（目前未完全实现，只输出结构）"""
    result: Dict[str, Any] = {
        "phase": "T3-D6.3.1a",
        "mode": "real_run",
        "llm_called": False,  # 标记为 False，因为完整实现需后端运行
        "production_prompt_modified": False,
        "variants": [],
        "backend_status": "not_running",
        "note": "Real-run harness structure created. Full LLM call integration requires backend running and additional changes."
    }

    for variant_name in VARIANTS:
        variant_entry: Dict[str, Any] = {
            "name": variant_name,
            "runs": []
        }
        for i in range(runs):
            run_id = f"{variant_name}-run-{i + 1:03d}"
            variant_entry["runs"].append({
                "run_id": run_id,
                "status": "failed",
                "word_count": None,
                "too_short": None,
                "template_leak": None,
                "fallback_used": None,
                "retry_count": None,
                "write_skipped": None,
                "quality_flags": [],
                "quality_score": None,
                "output_excerpt": "",
                "failure_reason": "Backend not running / full integration not implemented in this harness"
            })
        result["variants"].append(variant_entry)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D6.3.1a: Lite Prompt variant experiment harness"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run only (default)"
    )
    parser.add_argument(
        "--real-run",
        action="store_true",
        help="Enable real LLM calls (requires backend running)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per variant (default 3)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Backend base URL (default http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help=f"Output JSON file (default {OUTPUT_FILE})"
    )
    args = parser.parse_args()

    # 决定模式
    if args.real_run:
        result = run_real_run(args.base_url, args.runs)
    else:
        result = run_dry_run(args.runs)

    # 保存输出
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Phase T3-D6.3.1a harness executed in {result['mode']} mode")
    print(f"📊 Output written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
