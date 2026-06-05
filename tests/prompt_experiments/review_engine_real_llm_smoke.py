#!/usr/bin/env python3
"""
Phase T3-D7.3c: Review Engine 真实 LLM Review 小冒烟脚本

- 默认 dry-run，不调用 LLM
- 只有显式 --real-run 才允许真实调用
- 只处理 3 条 candidates
- 不自动入库，不自动改正文
- 安全要求：不打印 API Key
"""

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

# 不自动导入后端模块，避免污染
# 只有 --real-run 时才尝试导入 LiteLLM

DEFAULT_PROMPT_TEMPLATE_PATH = "docs/testing/prompt-experiments/review-engine-llm-review-prompt-template.md"
DEFAULT_CANDIDATES_PATH = "tests/fixtures/review_engine_validator/llm_review_prompt_candidates_3items.json"
DEFAULT_OUTPUT_JSON_PATH = "docs/testing/prompt-experiments/review-engine-real-llm-smoke-output.json"
DEFAULT_OUTPUT_MD_PATH = "docs/testing/prompt-experiments/review-engine-real-llm-smoke-report.md"


def load_prompt_template(template_path: Path) -> str:
    """加载 Prompt 模板"""
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {template_path}")
    return template_path.read_text(encoding="utf-8")


def load_candidates(candidates_path: Path) -> Dict[str, Any]:
    """加载 Candidates JSON"""
    if not candidates_path.exists():
        raise FileNotFoundError(f"Candidates 文件不存在: {candidates_path}")
    with open(candidates_path, encoding="utf-8") as f:
        return json.load(f)


def build_prompt_for_llm(template_text: str, candidates_data: Dict[str, Any]) -> str:
    """构建完整的 LLM 输入 Prompt"""
    # 只提取我们需要的 items 部分
    items_part = json.dumps(
        {
            "phase": candidates_data.get("phase", "T3-D7.1.1"),
            "engine": candidates_data.get("engine", "diff_engine"),
            "items": candidates_data.get("items", [])
        },
        ensure_ascii=False,
        indent=2
    )
    return f"""{template_text}\n\n---\n\n[INPUT CANDIDATES]\n{items_part}"""


def run_dry_run(template_text: str, candidates_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Dry-run 模式：不调用 LLM，返回模拟结果"""
    print("⚠️  DRY-RUN 模式：不调用真实 LLM")
    print("ℹ️   使用预设的 mock output 进行验证")

    # 使用已有的 mock output
    mock_output_path = Path("tests/fixtures/review_engine_validator/llm_review_prompt_output_sample.json")
    if not mock_output_path.exists():
        raise FileNotFoundError(f"Mock output 不存在: {mock_output_path}")

    with open(mock_output_path, encoding="utf-8") as f:
        mock_output = json.load(f)

    # 稍微修改 metadata 标记为 dry-run
    mock_output["phase"] = "T3-D7.3c"
    mock_output["mode"] = "dry_run_smoke"
    mock_output["llm_called"] = False
    mock_output["review_metadata"] = mock_output.get("review_metadata", {})
    mock_output["review_metadata"]["note"] = "DRY-RUN: Mock output for smoke test"

    return mock_output, "DRY-RUN: 使用预设 mock output"


def run_real_run(template_text: str, candidates_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Real-run 模式：调用真实 LLM（仅当 --real-run 时执行）"""
    print("🚀 REAL-RUN 模式：尝试调用真实 LLM")

    # 简单的 LiteLLM 调用封装（不依赖后端模块）
    try:
        import litellm
    except ImportError:
        raise RuntimeError("缺少依赖: pip install litellm")

    # 检查是否有 .env 或可用配置（不打印具体值）
    llm_configured = False
    llm_provider = "unknown"
    llm_model = "unknown"

    # 尝试从环境或简单配置读取（不打印密钥）
    import os
    from dotenv import load_dotenv
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            llm_configured = True
            llm_provider = os.getenv("LLM_PROVIDER", "openai")
            llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not llm_configured:
        raise RuntimeError("LLM 配置未找到。缺少 API Key 或相关配置。")

    # 构建完整 Prompt
    full_prompt = build_prompt_for_llm(template_text, candidates_data)

    # 调用 LLM（只打印 provider/model，不打印 key）
    print(f"ℹ️   调用 LLM: provider={llm_provider}, model={llm_model}")

    try:
        # 简单的非流式调用
        response = litellm.completion(
            model=llm_model,
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=2000,
            temperature=0.1
        )
        raw_output = response.choices[0].message.content.strip()

        # 尝试提取 JSON
        json_start = raw_output.find("{")
        json_end = raw_output.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("LLM 输出中未找到有效 JSON")

        json_str = raw_output[json_start:json_end]
        llm_review_output = json.loads(json_str)

        # 确保字段正确
        llm_review_output.setdefault("phase", "T3-D7.3c")
        llm_review_output.setdefault("engine", "review_engine")
        llm_review_output.setdefault("mode", "real_llm_smoke")
        llm_review_output.setdefault("llm_called", True)
        llm_review_output.setdefault("auto_write_settings", False)

        return llm_review_output, "REAL-RUN: LLM 调用成功"
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败: {type(e).__name__}: {str(e)}") from e


def generate_report_md(
    output_json: Dict[str, Any],
    status: str,
    note: str,
    output_path: Path
):
    """生成 Markdown 报告"""
    lines = [
        "# Review Engine 真实 LLM Review 小冒烟报告",
        "",
        f"- **Phase**: T3-D7.3c",
        f"- **Status**: {status}",
        f"- **Mode**: {output_json.get('mode', 'unknown')}",
        f"- **LLM Called**: {'Yes' if output_json.get('llm_called', False) else 'No'}",
        f"- **Note**: {note}",
        "",
        "## 统计",
        "",
        f"- Total Candidates: {len(output_json.get('reviews', []))}",
        "",
        "## 输出 JSON",
        "",
        "```json",
        json.dumps(output_json, ensure_ascii=False, indent=2),
        "```",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_failure_report(
    failure_type: str,
    failure_reason: str,
    output_path: Path
):
    """生成失败报告"""
    lines = [
        "# Review Engine 真实 LLM Review 小冒烟 - 失败报告",
        "",
        f"- **Phase**: T3-D7.3c",
        f"- **Status**: ❌ FAILED",
        f"- **Failure Type**: {failure_type}",
        f"- **Failure Reason**: {failure_reason}",
        "",
        "## 说明",
        "",
        "- 环境可能缺少 LLM 配置（.env 中的 API Key）",
        "- 服务可能不可用",
        "- 请检查并重新运行 --real-run",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.3c: Review Engine 真实 LLM Review 小冒烟"
    )
    parser.add_argument("--prompt-template", type=Path, default=DEFAULT_PROMPT_TEMPLATE_PATH,
                        help=f"Prompt 模板路径 (默认: {DEFAULT_PROMPT_TEMPLATE_PATH})")
    parser.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES_PATH,
                        help=f"Candidates JSON 路径 (默认: {DEFAULT_CANDIDATES_PATH})")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON_PATH,
                        help=f"输出 JSON 路径 (默认: {DEFAULT_OUTPUT_JSON_PATH})")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD_PATH,
                        help=f"输出 Markdown 报告路径 (默认: {DEFAULT_OUTPUT_MD_PATH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry-run 模式 (不调用 LLM，默认)")
    parser.add_argument("--real-run", action="store_true",
                        help="Real-run 模式 (允许调用真实 LLM)")

    args = parser.parse_args()

    print("=" * 60)
    print("Phase T3-D7.3c: Review Engine 真实 LLM Review 小冒烟")
    print("=" * 60)
    print()

    # 决定运行模式：默认 dry-run，只有显式 --real-run 才允许真实调用
    is_real_run = args.real_run
    if is_real_run:
        mode = "REAL-RUN"
    else:
        mode = "DRY-RUN"
        print("ℹ️  默认使用 DRY-RUN 模式，如需真实调用请添加 --real-run")

    print(f"ℹ️   运行模式: {mode}")
    print()

    status = "✅ SUCCESS"
    failure_type = None
    failure_reason = None
    output_json = {}
    note = ""

    try:
        # 1. 加载 Prompt 模板和 Candidates
        template_text = load_prompt_template(args.prompt_template)
        candidates_data = load_candidates(args.candidates_json)
        print(f"✅ 加载 Prompt 模板: {args.prompt_template}")
        print(f"✅ 加载 Candidates: {args.candidates_json}")
        print(f"ℹ️   待处理 Candidate 数量: {len(candidates_data.get('items', []))}")
        print()

        # 2. 运行对应的模式
        if is_real_run:
            output_json, note = run_real_run(template_text, candidates_data)
        else:
            output_json, note = run_dry_run(template_text, candidates_data)

        # 3. 保存输出
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(output_json, f, ensure_ascii=False, indent=2)
        print(f"✅ 保存输出 JSON: {args.output_json}")

        # 4. 生成 Markdown 报告
        generate_report_md(output_json, status, note, args.output_md)
        print(f"✅ 生成 Markdown 报告: {args.output_md}")
        print()

    except Exception as e:
        status = "❌ FAILED"
        failure_type = type(e).__name__
        failure_reason = str(e)
        tb_str = traceback.format_exc()
        print(f"❌ 发生错误: {failure_type}: {failure_reason}")
        print(f"Stack trace:\n{tb_str}")

        # 生成失败报告
        failure_md_path = Path(str(args.output_md).replace(".md", "-failure.md"))
        generate_failure_report(failure_type, failure_reason, failure_md_path)
        print(f"✅ 生成失败报告: {failure_md_path}")

    print()
    print("=" * 60)
    print(f"结果: {status}")
    print("=" * 60)

    if failure_type:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
