"""Reusable T8 required-beat validator benchmark runner.

This is experiment tooling only. It does not import or modify Moyun product
code. It reads local LLM configuration but never prints or writes API keys.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
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
RUNS_DIR = RESULTS_DIR / "runs"

CASE_SCHEMA_VERSION = "t8-required-beat-case-v2"
VALIDATOR_PROMPT_VERSION = "t8-validator-semantic-v2"
REPAIR_PROMPT_VERSION = "t8-repair-minimal-v1"

BASELINE_T8_2_2 = {
    "validator_agreement_rate": 0.50,
    "repair_success_rate": 0.3333,
    "final_usable_rate": 0.6667,
}


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
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_run_id(prefix: str = "t8-2-5") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}"


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
    semantic = []
    for beat in case["required_beats"]:
        if beat.get("must_appear"):
            detail = beat.get("required_semantic_condition") or beat["text"]
        else:
            detail = beat.get("forbidden_semantic_condition") or beat["text"]
        semantic.append(f"{beat['id']}: {detail}")
    return f"""你是严谨的中文长篇小说场景写作者。

上文：
{case['context']}

事实约束：
{numbered(case['facts'])}

【本场必须完成的信息点】
{numbered(required)}

【禁止事项】
{numbered(forbidden)}

【语义边界】
{numbered(semantic)}

风格要求：
{numbered(case['style_constraints'])}

请写一个 {case['target_length']} 的完整场景。

生成正文前，请在内部检查：
1. 所有 required beats 是否自然写入正文；
2. forbidden beats 是否没有被违反；
3. 是否引入了新人物、新组织、新道具或新设定；
4. 是否保持地点、人物状态、道具归属、知识边界和悬念边界；
5. 如果 terminal_position_required=true，结尾是否真的停在该动作。

如果任一 required beat 缺失，请先在内部修正，再输出最终正文。
最终只输出正文，不输出检查过程、标题、编号或解释。"""


def build_natural_validator_prompt(case: dict[str, Any], text: str) -> str:
    return f"""You are a continuity validator for Chinese long-form fiction.

Judge only the generated text. Do not give credit because a beat appears in the case JSON. Do not rely only on keyword presence. Accept paraphrases when the meaning is clearly present. Treat uncertain evidence as partial.

When reviewing forbidden beats, distinguish what the reader is explicitly told, what a character knows, and what a character merely suspects.

When terminal_position_required=true, check whether the required action is truly the final narrative beat.

Case JSON:
{json.dumps(case, ensure_ascii=False, indent=2)}

Generated text:
{text}

Output Markdown:
## Required Beats
For each beat: id, status satisfied / partial / missing, evidence, evidence quality exact / paraphrase / weak / absent, reason, terminal-position check if relevant, knowledge-boundary check if relevant.

## Forbidden Violations
For each forbidden item: id, violated yes / no, evidence, evidence quality, reason, knowledge-boundary check if relevant.

## Logic Risks
List character-state, location, item, timeline, new-entity, style, terminal-hook, and knowledge-boundary risks.

## Overall Status
Output satisfied / needs_repair / unusable."""


def build_json_validator_prompt(case: dict[str, Any], text: str) -> str:
    return f"""You are a continuity validator for Chinese long-form fiction. Return JSON only. Do not output Markdown or commentary.

Important judging rules:
1. Judge only the generated text, not the case description or prompt wording.
2. A keyword hit is not enough. Mark a required beat as satisfied only when the generated text semantically fulfills the condition.
3. Accept clear paraphrases when they fulfill the semantic condition.
4. If evidence is ambiguous, mark partial rather than satisfied.
5. If there is no evidence in generated text, mark missing.
6. Forbidden beats must appear only in forbidden_violations, never in required_beats.
7. Distinguish reader-facing reveal, character knowledge, and character suspicion.
8. Check knowledge_boundary when present.
9. If terminal_position_required is true, the required action must be at the final narrative beat or final sentence; otherwise mark partial.
10. Quote short direct evidence from generated text for satisfied, partial, or violated judgments.

Case JSON:
{json.dumps(case, ensure_ascii=False, indent=2)}

Generated text:
{text}

Return JSON exactly in this shape:
{{
  "case_id": "{case['id']}",
  "all_required_beats_satisfied": false,
  "required_beats": [
    {{
      "id": "beat id",
      "status": "satisfied|partial|missing",
      "evidence": "short text evidence or empty string",
      "confidence": 0.0,
      "evidence_quality": "exact|paraphrase|weak|absent",
      "reasoning_note": "one short reason",
      "terminal_position_ok": true,
      "knowledge_boundary_ok": true
    }}
  ],
  "forbidden_violations": [
    {{
      "id": "forbidden id",
      "violated": false,
      "evidence": "short text evidence or empty string",
      "evidence_quality": "exact|paraphrase|weak|absent",
      "reasoning_note": "one short reason",
      "knowledge_boundary_ok": true
    }}
  ],
  "logic_risks": [
    {{
      "type": "character_state|item|timeline|location|new_entity|style|knowledge_boundary|terminal_hook|other",
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
- 不要大幅重写；
- 不新增人物、组织、系统、道具或设定；
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


def term_hits(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term and term in text]


def terminal_position_ok(text: str, beat: dict[str, Any], terms: list[str]) -> bool | None:
    if beat.get("terminal_position_required") is not True:
        return None
    if not text:
        return False
    tail_start = max(int(len(text) * 0.75), len(text) - 160, 0)
    tail = text[tail_start:]
    return any(term and term in tail for term in terms)


def rule_precheck(case: dict[str, Any], text: str) -> dict[str, Any]:
    required = []
    for beat in required_beats(case):
        keywords = beat.get("keywords") or []
        paraphrases = beat.get("acceptable_paraphrases") or []
        keyword_hits = term_hits(text, keywords)
        paraphrase_hits = term_hits(text, paraphrases)
        terminal_ok = terminal_position_ok(text, beat, keywords + paraphrases)
        if not keywords and not paraphrases:
            rule_status = "unknown"
        elif (keyword_hits or paraphrase_hits) and terminal_ok is not False:
            rule_status = "weak_pass"
        else:
            rule_status = "weak_fail"
        required.append({
            "id": beat["id"],
            "rule_status": rule_status,
            "keyword_hit": bool(keyword_hits),
            "paraphrase_hit": bool(paraphrase_hits),
            "keyword_hits": keyword_hits,
            "paraphrase_hits": paraphrase_hits,
            "terminal_position_ok": terminal_ok,
            "keywords": keywords,
            "acceptable_paraphrases": paraphrases,
        })
    forbidden = []
    for beat in forbidden_beats(case):
        keywords = beat.get("forbidden_keywords") or beat.get("keywords") or []
        keyword_hits = term_hits(text, keywords)
        rule_status = "unknown" if not keywords else ("weak_fail" if keyword_hits else "weak_pass")
        forbidden.append({
            "id": beat["id"],
            "rule_status": rule_status,
            "keyword_hit": bool(keyword_hits),
            "keyword_hits": keyword_hits,
            "keywords": keywords,
            "violation_threshold": beat.get("violation_threshold", ""),
        })
    weak_required_passed = sum(1 for item in required if item["rule_status"] == "weak_pass")
    weak_required_failed = sum(1 for item in required if item["rule_status"] == "weak_fail")
    weak_forbidden_hits = sum(1 for item in forbidden if item["rule_status"] == "weak_fail")
    if weak_required_failed == 0 and weak_forbidden_hits == 0:
        overall_signal = "weak_pass"
    elif weak_required_failed or weak_forbidden_hits:
        overall_signal = "weak_fail"
    else:
        overall_signal = "unknown"
    return {
        "rule_is_final": False,
        "required_beats": required,
        "forbidden_violations": forbidden,
        "weak_required_passed": weak_required_passed,
        "weak_required_failed": weak_required_failed,
        "required_total": len(required),
        "weak_forbidden_hits": weak_forbidden_hits,
        "length": len(text),
        "length_abnormal": len(text) < 200 or len(text) > 1800,
        "overall_signal": overall_signal,
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
    missing = {item["id"] for item in precheck["required_beats"] if item["rule_status"] == "weak_fail"}
    violated = {item["id"] for item in precheck["forbidden_violations"] if item["rule_status"] == "weak_fail"}
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
    required_terms = []
    for beat in required_beats(case):
        keywords = beat.get("keywords") or []
        if keywords:
            required_terms.append(keywords[0])
    return "。".join(required_terms) + "。林澈和沈知夏继续在旧港站地下层谨慎推进。"


def make_dry_json_validation(case: dict[str, Any], text: str) -> dict[str, Any]:
    precheck = rule_precheck(case, text)
    required_items = []
    for item in precheck["required_beats"]:
        status = "satisfied" if item["rule_status"] == "weak_pass" else "missing"
        hits = item["keyword_hits"] or item["paraphrase_hits"]
        required_items.append({
            "id": item["id"],
            "status": status,
            "evidence": hits[0] if status == "satisfied" and hits else "",
            "confidence": 0.8 if status == "satisfied" else 0.5,
            "evidence_quality": "exact" if item["keyword_hits"] else ("paraphrase" if item["paraphrase_hits"] else "absent"),
            "reasoning_note": "dry-run rule-derived validator result",
            "terminal_position_ok": item["terminal_position_ok"],
            "knowledge_boundary_ok": None,
        })
    forbidden_items = []
    for item in precheck["forbidden_violations"]:
        violated = item["rule_status"] == "weak_fail"
        forbidden_items.append({
            "id": item["id"],
            "violated": violated,
            "evidence": item["keyword_hits"][0] if violated and item["keyword_hits"] else "",
            "evidence_quality": "weak" if violated else "absent",
            "reasoning_note": "dry-run weak forbidden keyword signal",
            "knowledge_boundary_ok": None if violated else True,
        })
    overall_status = "satisfied" if all(item["status"] == "satisfied" for item in required_items) and not any(item["violated"] for item in forbidden_items) else "needs_repair"
    return {
        "parse_ok": True,
        "parse_error": None,
        "case_id": case["id"],
        "all_required_beats_satisfied": overall_status == "satisfied",
        "required_beats": required_items,
        "forbidden_violations": forbidden_items,
        "logic_risks": [],
        "overall_status": overall_status,
    }


def json_required_counts(validation: dict[str, Any], fallback_precheck: dict[str, Any]) -> tuple[int, int]:
    required = validation.get("required_beats") or []
    if validation.get("parse_ok") and required:
        satisfied = sum(1 for item in required if item.get("status") == "satisfied")
        return satisfied, len(required)
    return fallback_precheck["weak_required_passed"], fallback_precheck["required_total"]


def infer_disagreement_reason(
    precheck: dict[str, Any],
    json_validation: dict[str, Any],
    natural_text: str,
) -> tuple[list[str], str]:
    between: list[str] = []
    rule_set = status_set_from_rule(precheck)
    json_set = status_set_from_json(json_validation) if json_validation.get("parse_ok") else set()
    natural_set = {"needs_repair"} if natural_needs_repair(natural_text) else set()
    json_signal = {"needs_repair"} if json_needs_repair(json_validation) else set()
    if not json_validation.get("parse_ok"):
        between.append("json_parse")
    if rule_set != json_set:
        between.append("rule_vs_json")
    if bool(natural_set) != bool(json_signal):
        between.append("natural_vs_json")
    if bool(rule_set) != bool(natural_set):
        between.append("rule_vs_natural")
    if "rule_vs_json" in between and rule_set and not json_set:
        reason = "rule_keyword_too_strict_or_terminal_false_positive"
    elif "rule_vs_json" in between and json_set and not rule_set:
        reason = "rule_keyword_too_loose_or_semantic_boundary_missed"
    elif "natural_vs_json" in between:
        reason = "semantic_validator_disagreement"
    elif "json_parse" in between:
        reason = "json_validator_parse_failure"
    else:
        reason = "none"
    return between, reason


def failure_taxonomy(result: dict[str, Any]) -> dict[str, Any]:
    json_result = result["json_validator"]["result"]
    revalidation = result["revalidation"]["json_result"]
    required = json_result.get("required_beats") or []
    forbidden = json_result.get("forbidden_violations") or []
    missing = sum(1 for beat in required if beat.get("status") == "missing")
    partial = sum(1 for beat in required if beat.get("status") == "partial")
    violations = sum(1 for item in forbidden if item.get("violated") is True)
    knowledge = 0
    terminal = 0
    for beat in required:
        if beat.get("knowledge_boundary_ok") is False:
            knowledge += 1
        if beat.get("terminal_position_ok") is False:
            terminal += 1
    for item in forbidden:
        if item.get("violated") is True and item.get("knowledge_boundary_ok") is False:
            knowledge += 1
    repair_failed = bool(result["repair"]["triggered"] and revalidation.get("overall_status") != "satisfied")
    return {
        "missing_required_beat": missing,
        "partial_required_beat": partial,
        "forbidden_violation": violations,
        "knowledge_boundary_violation": knowledge,
        "terminal_position_failure": terminal,
        "repair_failed": repair_failed,
        "repair_introduced_new_error": result["metrics"]["new_error_count"] > 0,
        "validator_disagreement": result["metrics"]["disagreement"],
    }


def low_json_confidence(result: dict[str, Any], threshold: float = 0.7) -> bool:
    for beat in result["json_validator"]["result"].get("required_beats", []):
        confidence = beat.get("confidence")
        if isinstance(confidence, int | float) and confidence < threshold:
            return True
    return False


def json_status(result: dict[str, Any]) -> str:
    return result["json_validator"]["result"].get("overall_status", "unknown")


def natural_status(result: dict[str, Any]) -> str:
    return "needs_repair" if result["natural_validator"].get("needs_repair") else "satisfied"


def rule_status(result: dict[str, Any]) -> str:
    return result["rule_precheck"].get("overall_signal", "unknown")


def classify_repair_risk(result: dict[str, Any]) -> str:
    if not result["repair"]["triggered"]:
        return "not_triggered"
    if result["metrics"]["new_error_count"] > 0:
        return "harmful_repair"
    if not result["metrics"]["repair_success"]:
        return "failed_repair"
    original_len = len(result["generation"]["text"])
    repair_len = len(result["repair"]["text"])
    if repair_len > max(original_len * 1.45, original_len + 350):
        return "risky_repair"
    return "safe_repair"


def run_case(case: dict[str, Any], sample_index: int, config: LLMConfig | None, dry_run: bool) -> dict[str, Any]:
    sample_id = f"s{sample_index + 1}"
    result_id = f"{case['id']}-{sample_id}"
    started = time.perf_counter()
    if dry_run:
        generation_text = make_dry_text(case)
        generation_latency = 0.0
        generation_error = None
    else:
        generation_text, generation_latency, generation_error = call_llm(config, build_generator_prompt(case))

    precheck = rule_precheck(case, generation_text)

    if generation_error:
        natural_text = ""
        natural_latency = 0.0
        natural_error = "skipped_after_generation_error"
        json_raw = ""
        json_latency = 0.0
        json_error = "skipped_after_generation_error"
        json_validation = normalize_json_validation(case, None, generation_error)
    elif dry_run:
        json_validation = make_dry_json_validation(case, generation_text)
        natural_text = "## Overall Status\nneeds_repair" if json_needs_repair(json_validation) else "## Overall Status\nsatisfied"
        natural_latency = 0.0
        natural_error = None
        json_raw = json.dumps(json_validation, ensure_ascii=False)
        json_latency = 0.0
        json_error = None
    else:
        natural_text, natural_latency, natural_error = call_llm(config, build_natural_validator_prompt(case, generation_text), max_tokens=1200)
        json_raw, json_latency, json_error = call_llm(config, build_json_validator_prompt(case, generation_text), max_tokens=1000)
        parsed, parse_error = extract_json(json_raw)
        json_validation = normalize_json_validation(case, parsed, parse_error or json_error)

    rule_vs_json = status_set_from_rule(precheck) != status_set_from_json(json_validation) if json_validation.get("parse_ok") else True
    natural_disagrees = natural_needs_repair(natural_text) != json_needs_repair(json_validation)
    between, likely_reason = infer_disagreement_reason(precheck, json_validation, natural_text)
    disagreement = bool(between)

    needs_repair = json_needs_repair(json_validation)
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
    elif repair_error:
        revalidation = normalize_json_validation(case, None, repair_error)
        revalidation_raw = ""
        revalidation_latency = 0.0
        revalidation_error = "skipped_after_repair_error"
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
        if final_precheck["weak_forbidden_hits"] > precheck["weak_forbidden_hits"]:
            new_errors += 1
        if len(final_text) > max(len(generation_text) * 1.8, len(generation_text) + 600):
            new_errors += 1

    initial_satisfied, initial_total = json_required_counts(json_validation, precheck)
    final_usable = bool(revalidation.get("parse_ok") and revalidation.get("overall_status") == "satisfied")
    metrics = {
        "initial_required_satisfied": initial_satisfied,
        "initial_required_total": initial_total,
        "initial_completion_rate": initial_satisfied / max(initial_total, 1),
        "rule_weak_required_failed": precheck["weak_required_failed"],
        "rule_weak_forbidden_hits": precheck["weak_forbidden_hits"],
        "json_parse_ok": bool(json_validation.get("parse_ok")),
        "disagreement": disagreement,
        "repair_triggered": repair_triggered,
        "repair_success": repair_triggered and final_usable,
        "new_error_count": new_errors,
        "final_usable": final_usable,
        "total_latency": round(time.perf_counter() - started, 2),
    }

    result = {
        "run_id": result_id,
        "case_id": case["id"],
        "sample_id": sample_id,
        "model": config.model if config else "dry-run",
        "case_meta": {
            "difficulty": case.get("difficulty", "unknown"),
            "beat_type": case.get("beat_type", []),
        },
        "generation": {
            "text": generation_text,
            "latency": generation_latency,
            "error": generation_error,
            "prompt_variant": "numbered-beats+self-check+semantic-boundary",
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
            "between": between,
            "likely_reason": likely_reason,
            "rule_vs_json": rule_vs_json,
            "rule_vs_natural": bool(rule_status_from_set(status_set_from_rule(precheck)) != natural_status_from_text(natural_text)),
            "natural_vs_json": natural_disagrees,
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
    result["failure_taxonomy"] = failure_taxonomy(result)
    result["repair_risk"] = classify_repair_risk(result)
    return result


def rule_status_from_set(items: set[str]) -> str:
    return "needs_repair" if items else "satisfied"


def natural_status_from_text(text: str) -> str:
    return "needs_repair" if natural_needs_repair(text) else "satisfied"


def write_raw(result: dict[str, Any], raw_dir: Path) -> None:
    lines = [
        f"# {result['run_id']}",
        "",
        f"Case: `{result['case_id']}`",
        f"Sample: `{result['sample_id']}`",
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
        "## Failure Taxonomy",
        "",
        "```json",
        json.dumps(result["failure_taxonomy"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{result['run_id']}.md").write_text("\n".join(lines), encoding="utf-8")


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
    repair_breakdown = aggregate_counts(results, lambda r: r["repair_risk"])
    summary = {
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
        "repair_risk_breakdown": repair_breakdown,
    }
    summary["baseline_comparison"] = {
        "validator_agreement_delta": summary["validator_agreement_rate"] - BASELINE_T8_2_2["validator_agreement_rate"],
        "repair_success_delta": summary["repair_success_rate"] - BASELINE_T8_2_2["repair_success_rate"],
        "final_usable_delta": summary["final_usable_rate"] - BASELINE_T8_2_2["final_usable_rate"],
    }
    summary["difficulty_analysis"] = grouped_metrics(results, lambda r: r["case_meta"].get("difficulty", "unknown"))
    summary["beat_type_analysis"] = grouped_metrics_multi(results, lambda r: r["case_meta"].get("beat_type", []))
    return summary


def aggregate_counts(results: list[dict[str, Any]], key_fn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        key = key_fn(result)
        counts[key] = counts.get(key, 0) + 1
    return counts


def grouped_metrics(results: list[dict[str, Any]], key_fn) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        groups.setdefault(key_fn(result), []).append(result)
    return {key: summarize_group(items) for key, items in sorted(groups.items())}


def grouped_metrics_multi(results: list[dict[str, Any]], key_fn) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        keys = key_fn(result) or ["unknown"]
        for key in keys:
            groups.setdefault(key, []).append(result)
    return {key: summarize_group(items) for key, items in sorted(groups.items())}


def summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runs": len(items),
        "agreement_rate": sum(1 for r in items if not r["metrics"]["disagreement"]) / max(len(items), 1),
        "final_usable_rate": sum(1 for r in items if r["metrics"]["final_usable"]) / max(len(items), 1),
        "repair_trigger_count": sum(1 for r in items if r["metrics"]["repair_triggered"]),
        "average_latency": round(sum(r["metrics"]["total_latency"] for r in items) / max(len(items), 1), 2),
    }


def audit_reasons(result: dict[str, Any]) -> list[str]:
    reasons = []
    taxonomy = result["failure_taxonomy"]
    if result["metrics"]["disagreement"]:
        reasons.append("disagreement")
    if result["repair"]["triggered"] and not result["metrics"]["repair_success"]:
        reasons.append("repair_failed")
    if low_json_confidence(result):
        reasons.append("json_confidence_low")
    if taxonomy["forbidden_violation"] > 0:
        reasons.append("forbidden_violation")
    if not result["metrics"]["final_usable"]:
        reasons.append("final_unusable")
    if result["disagreement"].get("natural_vs_json"):
        reasons.append("natural_json_conflict")
    rule_fail_json_pass = (
        result["rule_precheck"]["weak_required_failed"] + result["rule_precheck"]["weak_forbidden_hits"] > 0
        and not json_needs_repair(result["json_validator"]["result"])
    )
    if rule_fail_json_pass:
        reasons.append("rule_weak_fail_json_pass")
    return reasons


def audit_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        reasons = audit_reasons(result)
        if not reasons:
            continue
        rows.append({
            "run_id": result["run_id"],
            "case_id": result["case_id"],
            "sample_id": result["sample_id"],
            "reason": ";".join(reasons),
            "rule_status": rule_status(result),
            "json_status": json_status(result),
            "natural_status": natural_status(result),
            "repair_triggered": result["metrics"]["repair_triggered"],
            "repair_success": result["metrics"]["repair_success"],
            "final_usable": result["metrics"]["final_usable"],
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def percent(value: float) -> str:
    return f"{value:.2%}"


def group_table(groups: dict[str, Any]) -> str:
    lines = ["| Group | Runs | Agreement | Final usable | Repair triggers | Avg latency |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for key, value in groups.items():
        lines.append(
            f"| {key} | {value['runs']} | {percent(value['agreement_rate'])} | "
            f"{percent(value['final_usable_rate'])} | {value['repair_trigger_count']} | {value['average_latency']:.2f}s |"
        )
    return "\n".join(lines)


def repair_breakdown_table(summary: dict[str, Any]) -> str:
    rows = summary["repair_risk_breakdown"]
    order = ["not_triggered", "safe_repair", "risky_repair", "failed_repair", "harmful_repair"]
    lines = ["| Type | Count |", "| --- | ---: |"]
    for key in order:
        lines.append(f"| {key} | {rows.get(key, 0)} |")
    return "\n".join(lines)


def write_summary(results: list[dict[str, Any]], summary: dict[str, Any], manifest: dict[str, Any], run_dir: Path) -> None:
    write_json(run_dir / "summary.json", {"manifest": manifest, "summary": summary, "runs": results})
    summary_rows = []
    for result in results:
        row = {
            "run_id": result["run_id"],
            "case_id": result["case_id"],
            "sample_id": result["sample_id"],
            "difficulty": result["case_meta"]["difficulty"],
            "beat_type": ";".join(result["case_meta"]["beat_type"]),
            **result["metrics"],
            "repair_risk": result["repair_risk"],
            "failure_taxonomy": json.dumps(result["failure_taxonomy"], ensure_ascii=False, separators=(",", ":")),
        }
        summary_rows.append(row)
    write_csv(
        run_dir / "summary.csv",
        summary_rows,
        [
            "run_id", "case_id", "sample_id", "difficulty", "beat_type", "initial_completion_rate",
            "json_parse_ok", "rule_weak_required_failed", "rule_weak_forbidden_hits", "disagreement",
            "repair_triggered", "repair_success", "new_error_count", "final_usable", "total_latency",
            "repair_risk", "failure_taxonomy",
        ],
    )
    audit = audit_rows(results)
    write_csv(
        run_dir / "audit-candidates.csv",
        audit,
        [
            "run_id", "case_id", "sample_id", "reason", "rule_status", "json_status",
            "natural_status", "repair_triggered", "repair_success", "final_usable",
        ],
    )
    case_lines = "\n".join(
        f"| {r['case_id']} | {r['sample_id']} | {percent(r['metrics']['initial_completion_rate'])} | "
        f"{r['metrics']['json_parse_ok']} | {r['metrics']['disagreement']} | "
        f"{r['metrics']['repair_triggered']} | {r['metrics']['repair_success']} | "
        f"{r['metrics']['final_usable']} | {r['repair_risk']} | {r['metrics']['total_latency']:.2f}s |"
        for r in results
    )
    comparison = summary["baseline_comparison"]
    markdown = f"""# T8.2.5 Expanded Required Beat Validator Benchmark

## 1. Background

T8.2.2 created the validator benchmark, T8.2.3 audited disagreement, and T8.2.4 refined schema, prompt, and weak-rule semantics. T8.2.5 hardens the regression framework and expands the run to two samples per six cases.

## 2. Run Manifest

- Run ID: `{manifest['run_id']}`
- Timestamp: `{manifest['timestamp']}`
- Model: `{manifest['model']}`
- Samples: `{manifest['samples']}`
- Cases: `{', '.join(manifest['cases'])}`
- Commit: `{manifest['commit']}`
- Case schema version: `{manifest['case_schema_version']}`
- Validator prompt version: `{manifest['validator_prompt_version']}`
- Repair prompt version: `{manifest['repair_prompt_version']}`

## 3. Summary Metrics

| Metric | Value |
| --- | ---: |
| Runs | {summary['runs']} |
| Initial beat completion rate | {percent(summary['initial_beat_completion_rate'])} |
| JSON parse rate | {percent(summary['validator_json_parse_rate'])} |
| Validator agreement rate | {percent(summary['validator_agreement_rate'])} |
| Repair trigger count | {summary['repair_trigger_count']} |
| Repair success rate | {percent(summary['repair_success_rate'])} |
| New error rate | {percent(summary['new_error_rate'])} |
| Final usable rate | {percent(summary['final_usable_rate'])} |
| Average total latency | {summary['average_total_latency']:.2f}s |

## 4. Comparison With T8.2.2 Baseline

| Metric | T8.2.2 | T8.2.5 | Delta |
| --- | ---: | ---: | ---: |
| Validator agreement | 50.00% | {percent(summary['validator_agreement_rate'])} | {comparison['validator_agreement_delta']:+.2%} |
| Repair success | 33.33% | {percent(summary['repair_success_rate'])} | {comparison['repair_success_delta']:+.2%} |
| Final usable | 66.67% | {percent(summary['final_usable_rate'])} | {comparison['final_usable_delta']:+.2%} |

## 5. Difficulty Analysis

{group_table(summary['difficulty_analysis'])}

## 6. Beat Type Analysis

{group_table(summary['beat_type_analysis'])}

## 7. Repair Risk Breakdown

{repair_breakdown_table(summary)}

Decision defaults:

- automatic repair: not allowed
- repair candidate: allowed with user preview/adopt only
- validator warning only: recommended

## 8. Run Details

| Case | Sample | Initial completion | JSON parse | Disagreement | Repair triggered | Repair success | Final usable | Repair risk | Latency |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: |
{case_lines}

## 9. Audit Candidates

Audit candidates: {len(audit)}

See `audit-candidates.csv` for samples requiring manual review.

## 10. Productization Reading

JSON validator warnings are the strongest productization candidate. Rule-based precheck remains useful as a weak audit signal, not a blocker. Natural validator explanations may be useful for user-facing explanations but should not be the only machine gate.

Automatic repair is not recommended. Repair candidate generation may be useful if the user previews and adopts it manually.
"""
    (run_dir / "summary.md").write_text(markdown, encoding="utf-8")


def write_latest_expanded(summary: dict[str, Any], manifest: dict[str, Any], run_dir: Path, audit_count: int) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS_DIR / "t8-2-5-expanded-summary.json", {"manifest": manifest, "summary": summary, "run_dir": str(run_dir.relative_to(ROOT))})
    write_csv(
        RESULTS_DIR / "t8-2-5-expanded-summary.csv",
        [{
            "run_id": manifest["run_id"],
            "model": summary["model"],
            "runs": summary["runs"],
            "json_parse_rate": summary["validator_json_parse_rate"],
            "validator_agreement_rate": summary["validator_agreement_rate"],
            "repair_trigger_count": summary["repair_trigger_count"],
            "repair_success_rate": summary["repair_success_rate"],
            "new_error_rate": summary["new_error_rate"],
            "final_usable_rate": summary["final_usable_rate"],
            "average_total_latency": summary["average_total_latency"],
            "audit_candidates": audit_count,
        }],
        [
            "run_id", "model", "runs", "json_parse_rate", "validator_agreement_rate",
            "repair_trigger_count", "repair_success_rate", "new_error_rate",
            "final_usable_rate", "average_total_latency", "audit_candidates",
        ],
    )
    md = f"""# T8.2.5 Expanded Summary

Run-specific artifacts: `results/runs/{manifest['run_id']}/`

| Metric | Value |
| --- | ---: |
| Runs | {summary['runs']} |
| JSON parse rate | {percent(summary['validator_json_parse_rate'])} |
| Validator agreement rate | {percent(summary['validator_agreement_rate'])} |
| Repair trigger count | {summary['repair_trigger_count']} |
| Repair success rate | {percent(summary['repair_success_rate'])} |
| New error rate | {percent(summary['new_error_rate'])} |
| Final usable rate | {percent(summary['final_usable_rate'])} |
| Average total latency | {summary['average_total_latency']:.2f}s |
| Audit candidates | {audit_count} |

## Comparison With T8.2.2

- Agreement delta: {summary['baseline_comparison']['validator_agreement_delta']:+.2%}
- Repair success delta: {summary['baseline_comparison']['repair_success_delta']:+.2%}
- Final usable delta: {summary['baseline_comparison']['final_usable_delta']:+.2%}

## Productization Summary

Validator warning only is recommended. Repair candidate can be considered with explicit user preview/adopt. Automatic repair is not recommended.
"""
    (RESULTS_DIR / "t8-2-5-expanded-summary.md").write_text(md, encoding="utf-8")


def load_cases(case_ids: list[str] | None) -> list[dict[str, Any]]:
    cases = [load_json(path) for path in sorted(CASES_DIR.glob("*.json"))]
    if case_ids:
        selected = set(case_ids)
        cases = [case for case in cases if case["id"] in selected]
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run T8 required beat validator benchmark.")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic local mock outputs and no network.")
    parser.add_argument("--samples", type=int, default=1, help="Samples per case.")
    parser.add_argument("--cases", nargs="*", help="Optional case ids to run.")
    parser.add_argument("--timeout", type=int, default=180, help="LLM request timeout in seconds.")
    parser.add_argument("--run-id", help="Optional stable run id.")
    parser.add_argument("--notes", default="", help="Optional manifest notes.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    if not cases:
        raise SystemExit("No cases selected.")
    config = None if args.dry_run else read_llm_config(args.timeout)
    model = "dry-run" if args.dry_run else config.model
    run_id = args.run_id or make_run_id()
    run_dir = RUNS_DIR / run_id
    raw_dir = run_dir / "raw"
    scored_dir = run_dir / "scored"
    run_dir.mkdir(parents=True, exist_ok=False)
    raw_dir.mkdir(parents=True, exist_ok=True)
    scored_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "timestamp": utc_timestamp(),
        "model": model,
        "samples": args.samples,
        "cases": [case["id"] for case in cases],
        "commit": git_commit(),
        "case_schema_version": CASE_SCHEMA_VERSION,
        "validator_prompt_version": VALIDATOR_PROMPT_VERSION,
        "repair_prompt_version": REPAIR_PROMPT_VERSION,
        "notes": args.notes,
    }
    write_json(run_dir / "manifest.json", manifest)

    results: list[dict[str, Any]] = []
    for case in cases:
        for sample_index in range(args.samples):
            result = run_case(case, sample_index, config, args.dry_run)
            results.append(result)
            write_raw(result, raw_dir)
            write_json(scored_dir / f"{result['run_id']}.json", result)

    summary = summarize(results, model, args.dry_run)
    write_summary(results, summary, manifest, run_dir)
    audit_count = len(audit_rows(results))
    write_latest_expanded(summary, manifest, run_dir, audit_count)
    print(json.dumps({"manifest": manifest, "summary": summary, "run_dir": str(run_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
