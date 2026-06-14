"""Required-beat validation helpers for candidate metadata.

This module is deliberately small and side-effect free except for the optional
LLM call. It does not repair content, block adoption, or write files.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.llm import LLMService

logger = logging.getLogger(__name__)

VALIDATOR_VERSION = "required-beat-validator-v1"


def is_beat_validation_enabled(extra_vars: dict | None) -> bool:
    """Return True only when explicitly opted in by caller extra_vars."""
    if not extra_vars:
        return False
    value = extra_vars.get("_enable_beat_validation")
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _normalize_beat_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        lines = [line.strip(" -\t") for line in value.splitlines()]
        if len(lines) <= 1 and "；" in value:
            lines = [part.strip() for part in value.split("；")]
        elif len(lines) <= 1 and ";" in value:
            lines = [part.strip() for part in value.split(";")]
        return [line for line in lines if line]
    if isinstance(value, dict):
        items: list[str] = []
        for key, val in value.items():
            if isinstance(val, str):
                items.append(val.strip())
            else:
                items.append(f"{key}: {val}")
        return [item for item in items if item]
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            if isinstance(item, str):
                items.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("beat") or item.get("description")
                if text:
                    items.append(str(text).strip())
            elif item is not None:
                items.append(str(item).strip())
        return [item for item in items if item]
    return [str(value).strip()] if str(value).strip() else []


def extract_beat_validation_inputs(extra_vars: dict | None) -> tuple[list[str], list[str]]:
    """Extract required/forbidden beat lists from pipeline extra_vars."""
    if not extra_vars:
        return [], []
    required = _normalize_beat_list(
        extra_vars.get("required_beats")
        or extra_vars.get("required_beats_text")
        or extra_vars.get("must_include")
    )
    forbidden = _normalize_beat_list(
        extra_vars.get("forbidden_beats")
        or extra_vars.get("forbidden_facts")
        or extra_vars.get("must_not_include")
    )
    return required, forbidden


def unknown_beat_validation(
    required_beats: list[str],
    forbidden_beats: list[str],
    reason: str = "validator_failed",
) -> dict[str, Any]:
    return {
        "enabled": True,
        "status": "unknown",
        "summary": "信息点检查未完成，请采用前人工预览确认。",
        "required_beats": [
            {"text": beat, "status": "unknown", "evidence": "", "confidence": 0}
            for beat in required_beats
        ],
        "forbidden_beats": [
            {"text": beat, "violated": None, "evidence": "", "confidence": 0}
            for beat in forbidden_beats
        ],
        "logic_risks": [],
        "validator": {
            "type": "llm-json",
            "version": VALIDATOR_VERSION,
            "reason": reason,
        },
    }


def _safe_json_loads(text: str) -> dict[str, Any]:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start:end + 1]
    return json.loads(stripped)


def normalize_beat_validation_result(
    raw: dict[str, Any],
    required_beats: list[str],
    forbidden_beats: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    required_raw = raw.get("required_beats")
    if not isinstance(required_raw, list):
        required_raw = []
    forbidden_raw = raw.get("forbidden_beats") or raw.get("forbidden_violations")
    if not isinstance(forbidden_raw, list):
        forbidden_raw = []

    required_items: list[dict[str, Any]] = []
    for index, beat in enumerate(required_beats):
        source = required_raw[index] if index < len(required_raw) and isinstance(required_raw[index], dict) else {}
        status = str(source.get("status") or source.get("result") or "unknown").strip().lower()
        if status in {"pass", "passed", "satisfied", "hit", "yes"}:
            status = "satisfied"
        elif status in {"partial", "weak"}:
            status = "partial"
        elif status in {"missing", "fail", "failed", "no"}:
            status = "missing"
        else:
            status = "unknown"
        required_items.append({
            "text": str(source.get("text") or source.get("beat") or beat),
            "status": status,
            "evidence": str(source.get("evidence") or ""),
            "confidence": source.get("confidence", 0),
        })

    forbidden_items: list[dict[str, Any]] = []
    for index, beat in enumerate(forbidden_beats):
        source = forbidden_raw[index] if index < len(forbidden_raw) and isinstance(forbidden_raw[index], dict) else {}
        violated = source.get("violated")
        if violated is None:
            status = str(source.get("status") or "").strip().lower()
            violated = status in {"violated", "fail", "failed", "yes", "true"}
        forbidden_items.append({
            "text": str(source.get("text") or source.get("beat") or beat),
            "violated": bool(violated),
            "evidence": str(source.get("evidence") or ""),
            "confidence": source.get("confidence", 0),
        })

    logic_risks = raw.get("logic_risks") if isinstance(raw.get("logic_risks"), list) else []
    has_warning = any(item["status"] in {"missing", "partial", "unknown"} for item in required_items)
    has_warning = has_warning or any(item["violated"] for item in forbidden_items)
    status = "warning" if has_warning else "pass"
    summary = str(raw.get("summary") or ("存在信息点风险，请采用前预览确认。" if has_warning else "必需信息点检查通过。"))

    return {
        "enabled": True,
        "status": status,
        "summary": summary,
        "required_beats": required_items,
        "forbidden_beats": forbidden_items,
        "logic_risks": logic_risks,
        "validator": {
            "type": "llm-json",
            "version": VALIDATOR_VERSION,
            "model": model or "",
        },
    }


class RequiredBeatValidator:
    """LLM-backed validator that returns metadata-safe JSON only."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def validate(
        self,
        content: str,
        required_beats: list[str],
        forbidden_beats: list[str] | None = None,
    ) -> dict[str, Any]:
        forbidden_beats = forbidden_beats or []
        if not required_beats and not forbidden_beats:
            return unknown_beat_validation(required_beats, forbidden_beats, "no_beats")

        prompt = self._build_prompt(content, required_beats, forbidden_beats)
        try:
            response = await self.llm_service.complete_sync(
                [
                    {"role": "system", "content": "你是小说正文信息点校验器，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=1600,
                timeout=60,
            )
            raw = _safe_json_loads(response)
            return normalize_beat_validation_result(
                raw,
                required_beats,
                forbidden_beats,
                model=getattr(self.llm_service.config, "model", None),
            )
        except Exception as exc:
            logger.warning("required beat validation failed: %s", type(exc).__name__)
            return unknown_beat_validation(required_beats, forbidden_beats, type(exc).__name__)

    @staticmethod
    def _build_prompt(content: str, required_beats: list[str], forbidden_beats: list[str]) -> str:
        required_lines = "\n".join(f"{idx + 1}. {beat}" for idx, beat in enumerate(required_beats)) or "无"
        forbidden_lines = "\n".join(f"{idx + 1}. {beat}" for idx, beat in enumerate(forbidden_beats)) or "无"
        return (
            "请检查候选正文是否满足必需信息点，并检查是否触犯禁止信息点。\n"
            "不要改写正文，不要给写作建议，只返回 JSON。\n\n"
            "必需信息点：\n"
            f"{required_lines}\n\n"
            "禁止信息点：\n"
            f"{forbidden_lines}\n\n"
            "候选正文：\n"
            f"{content}\n\n"
            "返回 JSON 格式：\n"
            "{\n"
            '  "summary": "一句中文结论",\n'
            '  "required_beats": [{"text": "...", "status": "satisfied|partial|missing", "evidence": "...", "confidence": 0.0}],\n'
            '  "forbidden_beats": [{"text": "...", "violated": false, "evidence": "...", "confidence": 0.0}],\n'
            '  "logic_risks": []\n'
            "}"
        )
