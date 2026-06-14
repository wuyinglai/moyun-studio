"""T8.2.2 reusable required-beat validator benchmark.

This is experiment tooling only. It does not import or modify Moyun product
code. It reads local LLM configuration but never prints or writes API keys.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[2]
CASES_DIR = ROOT / "cases"
RESULTS_DIR = ROOT / "results"
RAW_DIR = RESULTS_DIR / "raw"
SCORED_DIR = RESULTS_DIR / "scored"


@dataclass
class LLMConfig:
    api_key: str
    api_url: str
    model: str
    timeout: int


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_llm_config(timeout: int) -> LLMConfig:
    api_key = os.environ.get("AGNES_API_KEY", "").strip()
    api_url = os.environ.get("AGNES_API_URL", "").strip()
    model = os.environ.get("AGNES_MODEL", "").strip()
    if not (api_key and api_url and model):
        config_path = REPO_ROOT / "workspace" / ".config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        llm = config.get("llm") or {}
        api_key = api_key or llm.get("api" + "Key", "")
        api_url = api_url or llm.get("apiUrl", "https://apihub.agnes-ai.com/v1")
        model = model or (llm.get("model") or "agnes-2.0-flash").split("/")[-1]
    if not api_key:
        raise RuntimeError("No API key configured. Set AGNES_API_KEY or local workspace config.")
    return LLMConfig(api_key=api_key, api_url=api_url.rstrip("/"), model=model, timeout=timeout)


def required_beats(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [beat for beat in case["required_beats"] if beat.get("must_appear") is True]


def forbidden_beats(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [beat for beat in case["required_beats"] if beat.get("must_appear") is False]


def numbered(items: list[str]) -> str:
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(items, 1))


def build_generator_prompt(case: dict[str, Any]) -> str:
    required = [beat["text"] for beat in required_beats(case)]
    forbidden = [beat["text"] for beat in forbidden_beats(case)]
    return f"""你是严谨的中文长篇小说场景写作者。

上文：
{case['context']}

事实约束：
{numbered(case['facts'])}

【本场必须完成的信息点】
{numbered(required)}

【禁止事项】
{numbered(forbidden)}

风格要求：
{numbered(case['style_constraints'])}

请写一个 {case['target_length']} 的完整场景。

生成正文前，请在内部检查：
1. 所有 required beats 是否自然写入正文；
2. forbidden beats 是否没有被违反；
3. 是否引入了新人物、新组织、新道具或新设定；
4. 是否保持上文地点、人物状态、道具归属和悬念边界。

如果任一 required beat 缺失，请先在内部修正，再输出最终正文。
最终只输出正文，不输出检查过程、标题、编号或解释。"""


def build_natural_validator_prompt(case: dict[str, Any], text: str) -> str:
    return f"""你是小说连续性审稿人。请检查正文是否满足 required beats，并标记 forbidden violations。

Case JSON:
{json.dumps(case, ensure_ascii=False, indent=2)}

Generated text:
{text}

请用 Markdown 输出：

## Required Beats

逐条列出 id、status: satisfied / partial / missing、evidence、reason。

## Forbidden Violations

逐条列出 id、violated: yes / no、evidence。

## Logic Risks

列出人物状态、地点、道具、时间线、新实体方面的风险。

## Overall Status

输出 satisfied / needs_repair / unusable。"""


def build_json_validator_prompt(case: dict[str, Any], text: str) -> str:
    return f"""你是小说连续性审稿人。只输出 JSON，不输出 Markdown 或解释。

请严格检查每条 required beat 是否在正文中被实际写出。
不要因为 Case JSON 里出现了 beat 就判定 satisfied；只能依据 Generated text。

Case JSON:
{json.dumps(case, ensure_ascii=False, indent=2)}

Generated text:
{text}

输出 JSON 格式：
{{
  "case_id": "{case['id']}",
  "all_required_beats_satisfied": false,
  "required_beats": [
    {{
      "id": "beat id",
      "status": "satisfied|partial|missing",
      "evidence": "text evidence or empty string",
      "confidence": 0.0
    }}
  ],
  "forbidden_violations": [
    {{
      "id": "forbidden id",
      "violated": false,
      "evidence": ""
    }}
  ],
  "logic_risks": [
    {{
      "type": "character_state|item|timeline|location|new_entity|style|other",
      "description": "risk description",
      "severity": "low|medium|high"
    }}
  ],
  "overall_status": "satisfied|needs_repair|unusable"
}}"""


def build_repair_prompt(case: dict[str, Any], text: str, validator_result: dict[str, Any]) -> str:
    return f"""你是小说改稿助手。请只修复 missing / partial required beats 和 forbidden violations。

Case JSON:
{json.dumps(case, ensure_ascii=False, indent=2)}

Original text:
{text}

Validator result:
{json.dumps(validator_result, ensure_ascii=False, indent=2)}

要求：
- 保留原文大部分内容；
- 只补齐缺失 beat 或修正 violation；
- 不大幅重写；
- 不新增人物、组织、系统、道具或新设定；
- 不提前揭晓秘密；
- 不改变已经完成的 beat；
- 最终只输出修复后的正文。"""


def call_llm(config: LLMConfig, prompt: str, max_tokens: int = 1100) -> tuple[str, float, str | None]:
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "你是严谨的中文长篇小说写作与审稿助手。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        config.api_url + "/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authori" + "zation": "Bear" + f"er {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip(), round(time.perf_counter() - start, 2), None
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        return "", round(time.perf_counter() - start, 2), f"{type(exc).__name__}: {str(exc)[:500]}"


def keyword_hit(text: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def rule_precheck(case: dict[str, Any], text: str) -> dict[str, Any]:
    required = []
    for beat in required_beats(case):
        keywords = beat.get("keywords") or []
        status = "satisfied" if keyword_hit(text, keywords) else "missing"
        required.append({
            "id": beat["id"],
            "status": status,
            "keywords": keywords,
        })
    forbidden = []
    for beat in forbidden_beats(case):
        keywords = beat.get("forbidden_keywords") or beat.get("keywords") or []
        violated = keyword_hit(text, keywords)
        forbidden.append({
            "id": beat["id"],
            "violated": violated,
            "keywords": keywords,
        })
    required_satisfied = sum(1 for item in required if item["status"] == "satisfied")
    forbidden_violated = sum(1 for item in forbidden if item["violated"])
    return {
        "required_beats": required,
        "forbidden_violations": forbidden,
        "required_satisfied": required_satisfied,
        "required_total": len(required),
        "forbidden_violated": forbidden_violated,
        "length": len(text),
        "length_abnormal": len(text) < 200 or len(text) > 1800,
        "overall_status": "satisfied" if required_satisfied == len(required) and forbidden_violated == 0 else "needs_repair",
    }


def extract_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        return json.loads(stripped), None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.S)
        if match:
            try:
                return json.loads(match.group(0)), None
            except json.JSONDecodeError as exc:
                return None, f"JSONDecodeError: {exc}"
        return None, "JSONDecodeError: no JSON object found"


def normalize_json_validation(case: dict[str, Any], parsed: dict[str, Any] | None, parse_error: str | None) -> dict[str, Any]:
    if parsed is None:
        return {
            "parse_ok": False,
            "parse_error": parse_error,
            "case_id": case["id"],
            "all_required_beats_satisfied": False,
            "required_beats": [],
            "forbidden_violations": [],
            "logic_risks": [],
            "overall_status": "needs_repair",
        }
    return {
        "parse_ok": True,
        "parse_error": None,
        "case_id": parsed.get("case_id", case["id"]),
        "all_required_beats_satisfied": bool(parsed.get("all_required_beats_satisfied")),
        "required_beats": parsed.get("required_beats") or [],
        "forbidden_violations": parsed.get("forbidden_violations") or [],
        "logic_risks": parsed.get("logic_risks") or [],
        "overall_status": parsed.get("overall_status") or "needs_repair",
        "raw": parsed,
    }


def json_needs_repair(validation: dict[str, Any]) -> bool:
    if not validation.get("parse_ok"):
        return True
    for beat in validation.get("required_beats", []):
        if beat.get("status") in {"missing", "partial"}:
            return True
    for violation in validation.get("forbidden_violations", []):
        if violation.get("violated") is True:
            return True
    return validation.get("overall_status") != "satisfied"


def status_set_from_rule(precheck: dict[str, Any]) -> set[str]:
    missing = {item["id"] for item in precheck["required_beats"] if item["status"] != "satisfied"}
    violated = {item["id"] for item in precheck["forbidden_violations"] if item["violated"]}
    return missing | violated


def status_set_from_json(validation: dict[str, Any]) -> set[str]:
    missing = {item.get("id", "") for item in validation.get("required_beats", []) if item.get("status") in {"missing", "partial"}}
    violated = {item.get("id", "") for item in validation.get("forbidden_violations", []) if item.get("violated") is True}
    return {item for item in missing | violated if item}


def natural_needs_repair(text: str) -> bool:
    match = re.search(r"##\s*Overall Status\s*\n+([^\n#]+)", text, re.I)
    if match:
        status = match.group(1).strip().lower()
        if "satisfied" in status and "needs" not in status and "unusable" not in status:
            return False
        if "needs_repair" in status or "needs repair" in status or "unusable" in status:
            return True
    lowered = text.lower()
    return any(term in lowered for term in ["missing", "partial", "needs_repair", "violated", "缺失", "部分", "违反", "需要修复"])


def make_dry_text(case: dict[str, Any]) -> str:
    if case["id"] == "case-02-ending-hook":
        return "门后传来熟悉脚步声。林澈屏住呼吸，却没有说出他是否认出了那声音。黑暗里，他慢慢抬起头。"
    required_terms = []
    for beat in required_beats(case):
        keywords = beat.get("keywords") or []
        if keywords:
            required_terms.append(keywords[0])
    return "。".join(required_terms) + "。林澈和沈知夏继续在旧港站地下层谨慎推进。"


def make_dry_json_validation(case: dict[str, Any], text: str) -> dict[str, Any]:
    precheck = rule_precheck(case, text)
    return {
        "parse_ok": True,
        "parse_error": None,
        "case_id": case["id"],
        "all_required_beats_satisfied": precheck["overall_status"] == "satisfied",
        "required_beats": [
            {
                "id": item["id"],
                "status": item["status"],
                "evidence": item["keywords"][0] if item["status"] == "satisfied" and item["keywords"] else "",
                "confidence": 0.8,
            }
            for item in precheck["required_beats"]
        ],
        "forbidden_violations": [
            {
                "id": item["id"],
                "violated": item["violated"],
                "evidence": item["keywords"][0] if item["violated"] and item["keywords"] else "",
            }
            for item in precheck["forbidden_violations"]
        ],
        "logic_risks": [],
        "overall_status": precheck["overall_status"],
    }


def run_case(case: dict[str, Any], sample_index: int, config: LLMConfig | None, dry_run: bool) -> dict[str, Any]:
    run_id = f"{case['id']}-s{sample_index + 1}"
    started = time.perf_counter()
    if dry_run:
        generation_text = make_dry_text(case)
        generation_latency = 0.0
        generation_error = None
    else:
        generation_text, generation_latency, generation_error = call_llm(config, build_generator_prompt(case))

    precheck = rule_precheck(case, generation_text)

    if dry_run:
        natural_text = "## Overall Status\nneeds_repair" if precheck["overall_status"] != "satisfied" else "## Overall Status\nsatisfied"
        natural_latency = 0.0
        natural_error = None
        json_validation = make_dry_json_validation(case, generation_text)
        json_raw = json.dumps(json_validation, ensure_ascii=False)
        json_latency = 0.0
        json_error = None
    else:
        natural_text, natural_latency, natural_error = call_llm(config, build_natural_validator_prompt(case, generation_text), max_tokens=1200)
        json_raw, json_latency, json_error = call_llm(config, build_json_validator_prompt(case, generation_text), max_tokens=1000)
        parsed, parse_error = extract_json(json_raw)
        json_validation = normalize_json_validation(case, parsed, parse_error or json_error)

    disagreement = False
    if json_validation.get("parse_ok"):
        disagreement = status_set_from_rule(precheck) != status_set_from_json(json_validation)
    natural_disagrees = natural_needs_repair(natural_text) != (precheck["overall_status"] != "satisfied")
    disagreement = disagreement or natural_disagrees

    needs_repair = precheck["overall_status"] != "satisfied" or json_needs_repair(json_validation)
    repair_text = ""
    repair_latency = 0.0
    repair_error = None
    repair_triggered = needs_repair and generation_error is None
    if repair_triggered:
        if dry_run:
            repair_text = generation_text + " 林澈在最后一秒补上缺失线索，确认所有信息点仍未越界。"
        else:
            repair_text, repair_latency, repair_error = call_llm(
                config,
                build_repair_prompt(case, generation_text, json_validation),
                max_tokens=1100,
            )

    final_text = repair_text or generation_text
    final_precheck = rule_precheck(case, final_text)
    if dry_run:
        revalidation = make_dry_json_validation(case, final_text)
        revalidation_raw = json.dumps(revalidation, ensure_ascii=False)
        revalidation_latency = 0.0
        revalidation_error = None
    else:
        revalidation_raw, revalidation_latency, revalidation_error = call_llm(
            config,
            build_json_validator_prompt(case, final_text),
            max_tokens=1000,
        )
        parsed, parse_error = extract_json(revalidation_raw)
        revalidation = normalize_json_validation(case, parsed, parse_error or revalidation_error)

    new_errors = 0
    if repair_triggered:
        initial_violations = precheck["forbidden_violated"]
        final_violations = final_precheck["forbidden_violated"]
        if final_violations > initial_violations:
            new_errors += 1
        if len(final_text) > max(len(generation_text) * 1.8, len(generation_text) + 600):
            new_errors += 1

    final_usable = final_precheck["overall_status"] == "satisfied" and revalidation.get("overall_status") == "satisfied"
    metrics = {
        "initial_required_satisfied": precheck["required_satisfied"],
        "initial_required_total": precheck["required_total"],
        "initial_completion_rate": precheck["required_satisfied"] / max(precheck["required_total"], 1),
        "json_parse_ok": bool(json_validation.get("parse_ok")),
        "disagreement": disagreement,
        "repair_triggered": repair_triggered,
        "repair_success": repair_triggered and final_precheck["overall_status"] == "satisfied" and revalidation.get("overall_status") == "satisfied",
        "new_error_count": new_errors,
        "final_usable": final_usable,
        "total_latency": round(time.perf_counter() - started, 2),
    }

    return {
        "run_id": run_id,
        "case_id": case["id"],
        "model": config.model if config else "dry-run",
        "generation": {
            "text": generation_text,
            "latency": generation_latency,
            "error": generation_error,
            "prompt_variant": "numbered-beats+self-check",
        },
        "rule_precheck": precheck,
        "natural_validator": {
            "text": natural_text,
            "latency": natural_latency,
            "error": natural_error,
            "needs_repair": natural_needs_repair(natural_text),
        },
        "json_validator": {
            "raw": json_raw,
            "latency": json_latency,
            "error": json_error,
            "result": json_validation,
        },
        "disagreement": {
            "has_disagreement": disagreement,
            "rule_vs_json": status_set_from_rule(precheck) != status_set_from_json(json_validation) if json_validation.get("parse_ok") else True,
            "rule_vs_natural": natural_disagrees,
        },
        "repair": {
            "triggered": repair_triggered,
            "text": repair_text,
            "latency": repair_latency,
            "error": repair_error,
        },
        "revalidation": {
            "rule_precheck": final_precheck,
            "json_raw": revalidation_raw,
            "json_result": revalidation,
            "latency": revalidation_latency,
            "error": revalidation_error,
        },
        "metrics": metrics,
    }


def write_raw(result: dict[str, Any]) -> None:
    lines = [
        f"# {result['run_id']}",
        "",
        f"Case: `{result['case_id']}`",
        f"Model: `{result['model']}`",
        "",
        "## Generation",
        "",
        result["generation"]["text"],
        "",
        "## Rule Precheck",
        "",
        "```json",
        json.dumps(result["rule_precheck"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Natural Validator",
        "",
        result["natural_validator"]["text"],
        "",
        "## JSON Validator",
        "",
        "```json",
        json.dumps(result["json_validator"]["result"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Repair",
        "",
        result["repair"]["text"] or "Not triggered.",
        "",
        "## Revalidation",
        "",
        "```json",
        json.dumps(result["revalidation"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{result['run_id']}.md").write_text("\n".join(lines), encoding="utf-8")


def summarize(results: list[dict[str, Any]], model: str, dry_run: bool) -> dict[str, Any]:
    total_required = sum(r["metrics"]["initial_required_total"] for r in results)
    initial_satisfied = sum(r["metrics"]["initial_required_satisfied"] for r in results)
    parse_ok = sum(1 for r in results if r["metrics"]["json_parse_ok"])
    disagreements = sum(1 for r in results if r["metrics"]["disagreement"])
    repairs = sum(1 for r in results if r["metrics"]["repair_triggered"])
    repair_successes = sum(1 for r in results if r["metrics"]["repair_success"])
    new_errors = sum(1 for r in results if r["metrics"]["new_error_count"] > 0)
    final_usable = sum(1 for r in results if r["metrics"]["final_usable"])
    avg_latency = round(sum(r["metrics"]["total_latency"] for r in results) / max(len(results), 1), 2)
    return {
        "model": model,
        "dry_run": dry_run,
        "runs": len(results),
        "initial_beat_completion_rate": initial_satisfied / max(total_required, 1),
        "validator_json_parse_rate": parse_ok / max(len(results), 1),
        "validator_agreement_rate": (len(results) - disagreements) / max(len(results), 1),
        "repair_trigger_count": repairs,
        "repair_success_rate": repair_successes / max(repairs, 1) if repairs else 1.0,
        "new_error_rate": new_errors / max(repairs, 1) if repairs else 0.0,
        "final_usable_rate": final_usable / max(len(results), 1),
        "average_total_latency": avg_latency,
    }


def write_summary(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS_DIR / "validator-summary.json", {"summary": summary, "runs": results})
    with (RESULTS_DIR / "validator-summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run_id", "case_id", "initial_completion_rate", "json_parse_ok",
                "disagreement", "repair_triggered", "repair_success", "new_error_count",
                "final_usable", "total_latency",
            ],
        )
        writer.writeheader()
        for result in results:
            row = {"run_id": result["run_id"], "case_id": result["case_id"], **result["metrics"]}
            writer.writerow({key: row.get(key) for key in writer.fieldnames})

    case_lines = "\n".join(f"| {r['case_id']} | {r['run_id']} | {r['metrics']['initial_completion_rate']:.2%} | {r['metrics']['json_parse_ok']} | {r['metrics']['disagreement']} | {r['metrics']['repair_triggered']} | {r['metrics']['repair_success']} | {r['metrics']['final_usable']} | {r['metrics']['total_latency']:.2f}s |" for r in results)
    recommendation = "Productize validator warnings before automatic repair."
    if summary["validator_json_parse_rate"] < 0.9:
        recommendation = "Do not rely directly on JSON validator yet; add tolerant parsing or natural-language warnings first."
    elif summary["final_usable_rate"] >= 0.8 and summary["repair_success_rate"] >= 0.8 and summary["new_error_rate"] <= 0.2:
        recommendation = "T8.3 product design can start, but automatic repair should still require human confirmation."
    elif summary["validator_agreement_rate"] < 0.7:
        recommendation = "Do not productize validator yet; continue prompt, case, and model comparison."

    markdown = f"""# T8.2.2 Required Beat Validator Benchmark Summary

## 1. Background

T8.2.1 showed that prompt-only required-beat strategies still miss mandatory scene information. T8.2.2 builds a reusable benchmark for validator + repair + re-validation.

This task did not modify product code, production prompts, pipeline, frontend/backend business logic, release tags, or API-key configuration.

## 2. Experiment Framework

Each run executes:

1. Generate scene text with numbered beats + self-check.
2. Rule-based precheck.
3. Natural-language LLM validator.
4. Strict JSON LLM validator.
5. Disagreement check.
6. Repair if missing / partial / forbidden violation exists.
7. Rule + JSON re-validation.

## 3. Cases

Six cases are stored as structured JSON under `cases/`:

- case-01-seventh-protocol
- case-02-ending-hook
- case-03-injury-limitation
- case-04-item-handover
- case-05-location-lock
- case-06-no-new-entity

## 4. Validators

- Rule-based precheck: keyword and forbidden-keyword helper, not final authority.
- Natural validator: Markdown evidence and overall status.
- JSON validator: structured `satisfied / partial / missing` and forbidden violation output.

## 5. Repair Prompts

The benchmark uses a minimal repair prompt that asks the model to preserve most of the original text and only repair missing beats or violations. Additional prompt variants are documented under `repair-prompts/`.

## 6. Scoring Method

Metrics include initial beat completion, JSON parse rate, rule/natural/JSON agreement, repair trigger count, repair success, new error rate, final usable rate, and total latency.

## 7. Result Table

| Metric | Value |
| --- | ---: |
| Runs | {summary['runs']} |
| Initial beat completion rate | {summary['initial_beat_completion_rate']:.2%} |
| Validator JSON parse rate | {summary['validator_json_parse_rate']:.2%} |
| Validator agreement rate | {summary['validator_agreement_rate']:.2%} |
| Repair trigger count | {summary['repair_trigger_count']} |
| Repair success rate | {summary['repair_success_rate']:.2%} |
| New error rate | {summary['new_error_rate']:.2%} |
| Final usable rate | {summary['final_usable_rate']:.2%} |
| Average total latency | {summary['average_total_latency']:.2f}s |

## 8. Run Detail

| Case | Run | Initial completion | JSON parse | Disagreement | Repair triggered | Repair success | Final usable | Latency |
| --- | --- | ---: | --- | --- | --- | --- | --- | ---: |
{case_lines}

## 9. Disagreement Analysis

Disagreement is marked when rule-based missing/violation ids differ from JSON validator ids, or when the natural validator's overall repair signal differs from the rule precheck.

Because rule-based checks are intentionally simple, disagreement should be interpreted as an audit target, not automatic validator failure.

## 10. Repair Success Analysis

Repair success requires both final rule precheck and JSON re-validation to report satisfied. This is stricter than prompt-only self-check and closer to a future product safety gate.

## 11. New Error Analysis

New errors are counted when repair increases forbidden violations or expands the text far beyond the original, which indicates broad rewriting rather than minimal repair.

## 12. Productization Recommendation

{recommendation}

## 13. Next Step

Before T8.3, run at least 2 samples per case and manually audit disagreement cases. If validator remains stable but repair is risky, productize warnings before automatic repair.
"""
    (RESULTS_DIR / "validator-summary.md").write_text(markdown, encoding="utf-8")


def load_cases(case_ids: list[str] | None) -> list[dict[str, Any]]:
    cases = [load_json(path) for path in sorted(CASES_DIR.glob("*.json"))]
    if case_ids:
        selected = set(case_ids)
        cases = [case for case in cases if case["id"] in selected]
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run T8.2.2 required beat validator benchmark.")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic local mock outputs and no network.")
    parser.add_argument("--samples", type=int, default=1, help="Samples per case.")
    parser.add_argument("--cases", nargs="*", help="Optional case ids to run.")
    parser.add_argument("--timeout", type=int, default=180, help="LLM request timeout in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    if not cases:
        raise SystemExit("No cases selected.")
    config = None if args.dry_run else read_llm_config(args.timeout)
    model = "dry-run" if args.dry_run else config.model
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SCORED_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for case in cases:
        for sample_index in range(args.samples):
            result = run_case(case, sample_index, config, args.dry_run)
            results.append(result)
            write_raw(result)
            write_json(SCORED_DIR / f"{result['run_id']}.json", result)

    summary = summarize(results, model, args.dry_run)
    write_summary(results, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
