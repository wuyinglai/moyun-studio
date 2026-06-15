"""Required-beat validation helpers for candidate metadata.

This module is deliberately small and side-effect free except for the optional
LLM call. It does not repair content, block adoption, or write files.
"""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
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


def _normalize_text(value: Any) -> str:
    """Normalize beat text for alignment without introducing dependencies."""
    text = str(value or "").lower()
    text = re.sub(r"[\s\-_*`~!！?？,，.。;；:：、\"'“”‘’《》()\[\]{}（）【】<>]", "", text)
    return text


def _extract_beat_id(value: dict[str, Any]) -> str:
    return str(value.get("id") or value.get("beat_id") or value.get("key") or "").strip()


def _extract_beat_text(value: dict[str, Any]) -> str:
    return str(value.get("text") or value.get("beat") or value.get("description") or "").strip()


def _similarity_score(left: str, right: str) -> float:
    left_norm = _normalize_text(left)
    right_norm = _normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _align_beat_result(
    expected_text: str,
    raw_items: list[dict[str, Any]],
    expected_index: int,
    expected_id: str,
    used_indexes: set[int],
    similarity_threshold: float = 0.62,
) -> tuple[dict[str, Any], str, float]:
    """Align one expected beat to one model-returned item.

    Order is deliberately the last fallback. The validator should never silently
    attach a low-similarity model result to a different required beat.
    """
    if expected_id:
        for index, item in enumerate(raw_items):
            if index in used_indexes:
                continue
            if _extract_beat_id(item) == expected_id:
                used_indexes.add(index)
                return item, "id", 1.0

    expected_norm = _normalize_text(expected_text)
    if expected_norm:
        for index, item in enumerate(raw_items):
            if index in used_indexes:
                continue
            item_norm = _normalize_text(_extract_beat_text(item))
            if item_norm and item_norm == expected_norm:
                used_indexes.add(index)
                return item, "text_exact", 1.0

    best_index = -1
    best_score = 0.0
    for index, item in enumerate(raw_items):
        if index in used_indexes:
            continue
        score = _similarity_score(expected_text, _extract_beat_text(item))
        if score > best_score:
            best_score = score
            best_index = index
    if best_index >= 0 and best_score >= similarity_threshold:
        used_indexes.add(best_index)
        return raw_items[best_index], "similarity", round(best_score, 4)

    # Preserve old behavior only when the model omitted text/id entirely but
    # returned an item at the same index. This keeps simple validators working
    # while still marking the alignment as weak for review.
    if expected_index < len(raw_items) and expected_index not in used_indexes:
        item = raw_items[expected_index]
        if not _extract_beat_id(item) and not _extract_beat_text(item):
            used_indexes.add(expected_index)
            return item, "index_unlabeled", 0.0

    return {}, "unknown", 0.0


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
    retry_count: int = 0,
    last_error_type: str = "",
) -> dict[str, Any]:
    return {
        "enabled": True,
        "status": "unknown",
        "summary": "信息点检查未完成，请采用前人工预览确认。",
        "required_beats": [
            {
                "id": f"beat-{idx + 1}",
                "text": beat,
                "status": "unknown",
                "evidence": "",
                "confidence": 0,
                "alignment": "unknown",
                "alignment_score": 0,
            }
            for idx, beat in enumerate(required_beats)
        ],
        "forbidden_beats": [
            {
                "id": f"forbid-{idx + 1}",
                "text": beat,
                "violated": None,
                "evidence": "",
                "confidence": 0,
                "alignment": "unknown",
                "alignment_score": 0,
            }
            for idx, beat in enumerate(forbidden_beats)
        ],
        "logic_risks": [],
        "validator": {
            "type": "llm-json",
            "version": VALIDATOR_VERSION,
            "reason": reason,
            "retry_count": retry_count,
            "last_error_type": last_error_type or reason,
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
    retry_count: int = 0,
    last_error_type: str = "",
) -> dict[str, Any]:
    required_raw = raw.get("required_beats")
    if not isinstance(required_raw, list):
        required_raw = []
    forbidden_raw = raw.get("forbidden_beats") or raw.get("forbidden_violations")
    if not isinstance(forbidden_raw, list):
        forbidden_raw = []

    required_items: list[dict[str, Any]] = []
    used_required_indexes: set[int] = set()
    for index, beat in enumerate(required_beats):
        expected_id = f"beat-{index + 1}"
        source, alignment_method, alignment_score = _align_beat_result(
            expected_text=beat,
            raw_items=[item for item in required_raw if isinstance(item, dict)],
            expected_index=index,
            expected_id=expected_id,
            used_indexes=used_required_indexes,
        )
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
            "id": str(source.get("id") or expected_id),
            "text": beat,
            "status": status,
            "evidence": str(source.get("evidence") or ""),
            "confidence": source.get("confidence", 0),
            "alignment": alignment_method,
            "alignment_score": alignment_score,
            "model_text": _extract_beat_text(source),
        })

    forbidden_items: list[dict[str, Any]] = []
    used_forbidden_indexes: set[int] = set()
    for index, beat in enumerate(forbidden_beats):
        expected_id = f"forbid-{index + 1}"
        source, alignment_method, alignment_score = _align_beat_result(
            expected_text=beat,
            raw_items=[item for item in forbidden_raw if isinstance(item, dict)],
            expected_index=index,
            expected_id=expected_id,
            used_indexes=used_forbidden_indexes,
        )
        violated = source.get("violated")
        if violated is None:
            status = str(source.get("status") or "").strip().lower()
            violated = status in {"violated", "fail", "failed", "yes", "true"}
        if alignment_method == "unknown":
            violated = None
        forbidden_items.append({
            "id": str(source.get("id") or expected_id),
            "text": beat,
            "violated": None if violated is None else bool(violated),
            "evidence": str(source.get("evidence") or ""),
            "confidence": source.get("confidence", 0),
            "alignment": alignment_method,
            "alignment_score": alignment_score,
            "model_text": _extract_beat_text(source),
        })

    logic_risks = raw.get("logic_risks") if isinstance(raw.get("logic_risks"), list) else []
    has_warning = any(item["status"] in {"missing", "partial", "unknown"} for item in required_items)
    has_warning = has_warning or any(item["violated"] is not False for item in forbidden_items)
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
            "retry_count": retry_count,
            "last_error_type": last_error_type,
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
        last_error_type = ""
        for attempt in range(2):
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
                    retry_count=attempt,
                    last_error_type=last_error_type,
                )
            except Exception as exc:
                last_error_type = type(exc).__name__
                logger.warning(
                    "required beat validation failed (attempt=%s): %s",
                    attempt + 1,
                    last_error_type,
                )
        return unknown_beat_validation(
            required_beats,
            forbidden_beats,
            last_error_type,
            retry_count=1,
            last_error_type=last_error_type,
        )

    @staticmethod
    def _build_prompt(content: str, required_beats: list[str], forbidden_beats: list[str]) -> str:
        required_lines = "\n".join(f"beat-{idx + 1}. {beat}" for idx, beat in enumerate(required_beats)) or "无"
        forbidden_lines = "\n".join(f"forbid-{idx + 1}. {beat}" for idx, beat in enumerate(forbidden_beats)) or "无"
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
            '  "required_beats": [{"id": "beat-1", "text": "...", "status": "satisfied|partial|missing", "evidence": "...", "confidence": 0.0}],\n'
            '  "forbidden_beats": [{"id": "forbid-1", "text": "...", "violated": false, "evidence": "...", "confidence": 0.0}],\n'
            '  "logic_risks": []\n'
            "}"
        )
