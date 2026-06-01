#!/usr/bin/env python3
"""Agnes API MCP stdio server.

This server intentionally reads the API key from AGNES_API_KEY at runtime.
Do not hardcode secrets in this file.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_LLM_MODEL = "agnes-2.0-flash"
DEFAULT_IMAGE_MODEL = "agnes-image-2.1-flash"
SERVER_NAME = "agnes-mcp"
SERVER_VERSION = "0.1.0"


def _redact(value: str) -> str:
    if not value:
        return value
    if value.startswith("sk-") and len(value) > 10:
        return f"{value[:6]}...{value[-4:]}"
    return value


def _api_key() -> str:
    key = os.environ.get("AGNES_API_KEY", "").strip()
    if not key:
        raise RuntimeError("AGNES_API_KEY is not set")
    return key


def _base_url() -> str:
    return os.environ.get("AGNES_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _post_json(path: str, payload: dict[str, Any], timeout: float = 120) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{_base_url()}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agnes API HTTP {exc.code}: {detail}") from exc

    if not raw:
        return {}
    return json.loads(raw)


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def agnes_chat(args: dict[str, Any]) -> str:
    prompt = str(args.get("prompt", "")).strip()
    messages = args.get("messages")
    system = str(args.get("system", "")).strip()
    if not messages:
        if not prompt:
            raise ValueError("prompt is required when messages is not provided")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": args.get("model") or os.environ.get("AGNES_LLM_MODEL") or DEFAULT_LLM_MODEL,
        "messages": messages,
    }
    for key in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty"):
        if key in args and args[key] is not None:
            payload[key] = args[key]

    data = _post_json("/chat/completions", payload, timeout=float(args.get("timeout", 120)))
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )
    return content if isinstance(content, str) else _json_text(data)


def agnes_image_generate(args: dict[str, Any]) -> str:
    prompt = str(args.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    payload: dict[str, Any] = {
        "model": args.get("model") or os.environ.get("AGNES_IMAGE_MODEL") or DEFAULT_IMAGE_MODEL,
        "prompt": prompt,
    }
    for key in ("n", "size", "quality", "style", "response_format"):
        if key in args and args[key] is not None:
            payload[key] = args[key]

    data = _post_json("/images/generations", payload, timeout=float(args.get("timeout", 180)))
    return _json_text(data)


def agnes_video_generate(args: dict[str, Any]) -> str:
    prompt = str(args.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    payload: dict[str, Any] = {
        "prompt": prompt,
    }
    if args.get("model"):
        payload["model"] = args["model"]
    for key in ("duration", "size", "resolution", "aspect_ratio", "fps", "response_format"):
        if key in args and args[key] is not None:
            payload[key] = args[key]
    if isinstance(args.get("extra"), dict):
        payload.update(args["extra"])

    data = _post_json("/videos", payload, timeout=float(args.get("timeout", 300)))
    return _json_text(data)


TOOLS: dict[str, dict[str, Any]] = {
    "agnes_chat": {
        "description": "Call Agnes LLM chat completions with agnes-2.0-flash by default.",
        "handler": agnes_chat,
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "system": {"type": "string"},
                "messages": {"type": "array", "items": {"type": "object"}},
                "model": {"type": "string", "default": DEFAULT_LLM_MODEL},
                "temperature": {"type": "number"},
                "top_p": {"type": "number"},
                "max_tokens": {"type": "integer"},
                "timeout": {"type": "number"},
            },
            "additionalProperties": True,
        },
    },
    "agnes_image_generate": {
        "description": "Generate images through Agnes image generations API.",
        "handler": agnes_image_generate,
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string", "default": DEFAULT_IMAGE_MODEL},
                "n": {"type": "integer", "default": 1},
                "size": {"type": "string"},
                "quality": {"type": "string"},
                "style": {"type": "string"},
                "response_format": {"type": "string"},
                "timeout": {"type": "number"},
            },
            "additionalProperties": True,
        },
    },
    "agnes_video_generate": {
        "description": "Generate videos through Agnes videos API.",
        "handler": agnes_video_generate,
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string"},
                "duration": {"type": "number"},
                "size": {"type": "string"},
                "resolution": {"type": "string"},
                "aspect_ratio": {"type": "string"},
                "fps": {"type": "integer"},
                "response_format": {"type": "string"},
                "extra": {"type": "object"},
                "timeout": {"type": "number"},
            },
            "additionalProperties": True,
        },
    },
}


def _tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": item["description"],
            "inputSchema": item["inputSchema"],
        }
        for name, item in TOOLS.items()
    ]


def _success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if request_id is None:
        return None

    try:
        if method == "initialize":
            return _success(request_id, {
                "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            })
        if method == "tools/list":
            return _success(request_id, {"tools": _tool_list()})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name not in TOOLS:
                return _error(request_id, -32602, f"Unknown tool: {name}")
            text = TOOLS[name]["handler"](args)
            return _success(request_id, {"content": [{"type": "text", "text": text}]})
        return _error(request_id, -32601, f"Method not found: {method}")
    except Exception as exc:
        message = str(exc)
        key = os.environ.get("AGNES_API_KEY", "").strip()
        if key:
            message = message.replace(key, "***").replace(_redact(key), "***")
        return _error(request_id, -32000, message)


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            response = _error(None, -32700, str(exc))
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
