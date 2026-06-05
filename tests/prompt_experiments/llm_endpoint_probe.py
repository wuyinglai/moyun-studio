#!/usr/bin/env python3
"""
Phase T3-D7.3c-b1: LLM Endpoint 配置探针

- 安全检测 LLM_API_BASE / LLM_PROVIDER / LLM_MODEL 的组合是否可用
- 默认 dry-run，不发请求
- 只输出 sanitized 配置信息，不打印 API Key
- 支持测试多个候选 provider/model 格式
"""

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_OUTPUT_MD = "docs/testing/prompt-experiments/llm-endpoint-probe-report.md"
DEFAULT_OUTPUT_JSON = "docs/testing/prompt-experiments/llm-endpoint-probe-report.json"


def get_llm_config_safely() -> Dict[str, Any]:
    """
    安全地获取 LLM 配置
    - 不打印 API Key
    - 只返回配置状态
    """
    import os
    from dotenv import load_dotenv

    config = {
        "provider": None,
        "model": None,
        "api_base": None,
        "provider_configured": False,
        "model_configured": False,
        "api_base_configured": False,
        "api_key_configured": False
    }

    # 尝试从 .env 加载
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    # 检查 API Key（不返回具体值）
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key and len(api_key) > 0:
        config["api_key_configured"] = True

    # 获取 provider
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider:
        config["provider"] = provider
        config["provider_configured"] = True

    # 获取 model
    model = os.getenv("LLM_MODEL", "").strip()
    if model:
        config["model"] = model
        config["model_configured"] = True

    # 获取 api_base
    api_base = os.getenv("LLM_API_BASE", "").strip()
    if api_base:
        config["api_base"] = api_base
        config["api_base_configured"] = True

    return config


def build_candidate_models(provider: str, model: str) -> List[str]:
    """
    根据 provider 和 model 构建候选模型名称列表
    """
    candidates = []
    
    if not provider or not model:
        return candidates

    # 移除可能的前缀
    model_clean = model
    if "/" in model_clean:
        model_clean = model_clean.split("/")[-1]

    # 测试多种格式
    candidates.append(f"openai/{model_clean}")
    candidates.append(f"custom_openai/{model_clean}")
    candidates.append(f"custom/{model_clean}")
    candidates.append(model_clean)  # 裸模型名
    
    # 如果 provider 是特定值，添加额外候选
    if provider == "deepseek":
        candidates.append(f"deepseek/{model_clean}")
    elif provider == "anthropic":
        candidates.append(f"anthropic/{model_clean}")
    elif provider == "ollama":
        candidates.append(f"ollama/{model_clean}")
    elif provider != "openai":
        candidates.append(f"{provider}/{model_clean}")

    return list(set(candidates))


def test_models_endpoint(api_base: str) -> Dict[str, Any]:
    """
    测试 /models 端点
    """
    import requests

    result = {
        "success": False,
        "status_code": None,
        "failure_type": None,
        "sanitized_failure_reason": None,
        "models_count": None
    }

    try:
        # 尝试多种 URL 格式
        urls_to_try = [
            api_base.rstrip("/"),
            api_base.rstrip("/") + "/v1",
            api_base.rstrip("/v1").rstrip("/") + "/v1"
        ]

        for base_url in urls_to_try:
            models_url = f"{base_url}/models"
            try:
                response = requests.get(models_url, timeout=10)
                result["status_code"] = response.status_code
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "data" in data:
                            result["models_count"] = len(data["data"])
                        result["success"] = True
                        return result
                    except:
                        pass
                
                # 记录非 200 状态码
                result["failure_type"] = "http_error"
                result["sanitized_failure_reason"] = f"HTTP {response.status_code}"
            except requests.exceptions.RequestException as e:
                result["failure_type"] = "connection_error"
                result["sanitized_failure_reason"] = str(type(e).__name__)

        return result
    except Exception as e:
        result["failure_type"] = "unknown_error"
        result["sanitized_failure_reason"] = str(type(e).__name__)
        return result


def test_chat_completion(model: str, api_base: str) -> Dict[str, Any]:
    """
    测试最小 chat completion 请求
    """
    import litellm

    result = {
        "success": False,
        "status_code": None,
        "failure_type": None,
        "sanitized_failure_reason": None,
        "model": model
    }

    try:
        litellm_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 10,
            "temperature": 0.1
        }

        if api_base:
            litellm_kwargs["api_base"] = api_base.rstrip("/")

        response = litellm.completion(**litellm_kwargs)
        result["success"] = True
        return result

    except litellm.exceptions.BadRequestError as e:
        result["failure_type"] = "bad_request"
        result["sanitized_failure_reason"] = str(type(e).__name__)
    except litellm.exceptions.AuthenticationError as e:
        result["failure_type"] = "authentication_error"
        result["sanitized_failure_reason"] = str(type(e).__name__)
    except litellm.exceptions.APIConnectionError as e:
        result["failure_type"] = "connection_error"
        result["sanitized_failure_reason"] = str(type(e).__name__)
    except litellm.exceptions.ProviderNotFoundError as e:
        result["failure_type"] = "provider_not_found"
        result["sanitized_failure_reason"] = str(type(e).__name__)
    except Exception as e:
        result["failure_type"] = "unknown_error"
        result["sanitized_failure_reason"] = str(type(e).__name__) + ": " + str(e)[:100]

    return result


def run_dry_run(config: Dict[str, Any]) -> Dict[str, Any]:
    """Dry-run 模式：不发请求，只验证配置"""
    print("⚠️  DRY-RUN 模式：不发送真实请求")
    
    candidate_models = build_candidate_models(config.get("provider", ""), config.get("model", ""))
    
    return {
        "phase": "T3-D7.3c-b1",
        "mode": "dry_run",
        "llm_called": False,
        "config": {
            "provider_configured": config["provider_configured"],
            "model_configured": config["model_configured"],
            "api_base_configured": config["api_base_configured"],
            "api_key_configured": config["api_key_configured"]
        },
        "candidate_models": candidate_models,
        "tests": [],
        "recommended_provider_model": None,
        "summary": {
            "message": "Dry-run 完成，未发送真实请求",
            "candidate_models_count": len(candidate_models)
        }
    }


def run_real_run(config: Dict[str, Any]) -> Dict[str, Any]:
    """Real-run 模式：发送真实请求测试 endpoint"""
    print("🚀 REAL-RUN 模式：发送真实请求测试 endpoint")
    
    results = {
        "phase": "T3-D7.3c-b1",
        "mode": "real_run",
        "llm_called": False,
        "config": {
            "provider_configured": config["provider_configured"],
            "model_configured": config["model_configured"],
            "api_base_configured": config["api_base_configured"],
            "api_key_configured": config["api_key_configured"]
        },
        "tests": [],
        "recommended_provider_model": None,
        "summary": {}
    }

    # 验证配置
    if not config["provider_configured"]:
        results["summary"] = {"message": "LLM_PROVIDER 未配置"}
        return results
    if not config["model_configured"]:
        results["summary"] = {"message": "LLM_MODEL 未配置"}
        return results
    if not config["api_base_configured"]:
        results["summary"] = {"message": "LLM_API_BASE 未配置"}
        return results
    if not config["api_key_configured"]:
        results["summary"] = {"message": "API Key 未配置"}
        return results

    print(f"ℹ️   配置摘要:")
    print(f"   - provider: {config['provider']}")
    print(f"   - model: {config['model']}")
    print(f"   - api_base: {config['api_base']}")
    print(f"   - api_key: 已配置 (不显示)")

    # 测试 /models 端点
    print("\n📡 测试 /models 端点...")
    models_result = test_models_endpoint(config["api_base"])
    results["tests"].append({
        "test_type": "models_endpoint",
        **models_result
    })

    # 测试 chat completion
    print("\n📡 测试 chat completion...")
    candidate_models = build_candidate_models(config["provider"], config["model"])
    print(f"   候选模型格式: {candidate_models}")

    success_count = 0
    recommended_model = None

    for candidate_model in candidate_models:
        print(f"   测试: {candidate_model}...")
        result = test_chat_completion(candidate_model, config["api_base"])
        
        results["tests"].append({
            "test_type": "chat_completion",
            **result
        })

        if result["success"]:
            success_count += 1
            recommended_model = candidate_model
            print(f"   ✓ 成功!")
        else:
            print(f"   ✗ 失败: {result['failure_type']} - {result['sanitized_failure_reason']}")

    # 更新摘要
    results["llm_called"] = True
    results["recommended_provider_model"] = recommended_model
    results["summary"] = {
        "message": f"测试完成，{success_count}/{len(candidate_models)} 个候选模型成功",
        "success_count": success_count,
        "total_tests": len(candidate_models)
    }

    return results


def generate_report_md(results: Dict[str, Any], output_path: Path):
    """生成 Markdown 报告"""
    lines = [
        "# LLM Endpoint 配置探针报告",
        "",
        f"- **Phase**: T3-D7.3c-b1",
        f"- **Mode**: {results.get('mode', 'unknown')}",
        f"- **LLM Called**: {'Yes' if results.get('llm_called', False) else 'No'}",
        "",
        "## 配置摘要 (Sanitized)",
        "",
        "| 配置项 | 状态 |",
        "|--------|------|",
        f"| Provider | {'✅ 已配置' if results['config'].get('provider_configured') else '❌ 未配置'} |",
        f"| Model | {'✅ 已配置' if results['config'].get('model_configured') else '❌ 未配置'} |",
        f"| API Base | {'✅ 已配置' if results['config'].get('api_base_configured') else '❌ 未配置'} |",
        f"| API Key | {'✅ 已配置' if results['config'].get('api_key_configured') else '❌ 未配置'} |",
        "",
    ]

    if "recommended_provider_model" in results and results["recommended_provider_model"]:
        lines.append("## 推荐配置")
        lines.append("")
        lines.append(f"**推荐模型格式**: `{results['recommended_provider_model']}`")
        lines.append("")

    if "tests" in results and results["tests"]:
        lines.append("## 测试结果")
        lines.append("")
        
        for test in results["tests"]:
            test_type = test.get("test_type", "unknown")
            success = test.get("success", False)
            model = test.get("model", "-")
            
            lines.append(f"### {test_type}")
            lines.append(f"- **模型**: {model}")
            lines.append(f"- **结果**: {'✅ 成功' if success else '❌ 失败'}")
            
            if not success:
                lines.append(f"- **失败类型**: {test.get('failure_type', '-')}")
                lines.append(f"- **失败原因**: {test.get('sanitized_failure_reason', '-')}")
            
            if "models_count" in test:
                lines.append(f"- **可用模型数**: {test['models_count']}")
            
            lines.append("")

    if "summary" in results:
        lines.append("## 摘要")
        lines.append("")
        lines.append(f"- {results['summary'].get('message', '-')}")
        
        if "success_count" in results["summary"]:
            lines.append(f"- 成功测试: {results['summary']['success_count']}/{results['summary']['total_tests']}")
        
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Phase T3-D7.3c-b1: LLM Endpoint 配置探针"
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Dry-run 模式 (默认开启，不发送请求)")
    parser.add_argument("--real-run", action="store_true",
                        help="Real-run 模式 (发送真实请求测试 endpoint)")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD,
                        help=f"输出 Markdown 报告路径")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON,
                        help=f"输出 JSON 报告路径")

    args = parser.parse_args()

    print("=" * 60)
    print("Phase T3-D7.3c-b1: LLM Endpoint 配置探针")
    print("=" * 60)
    print()

    # 决定运行模式
    is_real_run = args.real_run
    if is_real_run:
        mode = "REAL-RUN"
    else:
        mode = "DRY-RUN"
        print("ℹ️  默认使用 DRY-RUN 模式，如需真实请求请添加 --real-run")

    print(f"ℹ️   运行模式: {mode}")
    print()

    # 获取配置（安全方式）
    config = get_llm_config_safely()

    # 运行测试
    if is_real_run:
        results = run_real_run(config)
    else:
        results = run_dry_run(config)

    # 保存 JSON 结果
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 保存输出 JSON: {args.output_json}")

    # 生成 Markdown 报告
    generate_report_md(results, args.output_md)
    print(f"✅ 生成 Markdown 报告: {args.output_md}")

    print()
    print("=" * 60)
    print(f"结果: {results['summary'].get('message', '完成')}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
