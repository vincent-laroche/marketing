from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

SECRET_KEYS = {
    "sessionid",
    "csrftoken",
    "ds_user_id",
    "mid",
    "ig_did",
    "authorization",
    "cookie",
    "x-csrftoken",
    "notion_token",
    "openai_api_key",
    "token",
    "api_key",
}

MAX_RICH_TEXT = 1900


def redact(value: str | None) -> str:
    if not value:
        return "<missing>"
    return "<set>"


def sanitize_mapping(data: Mapping[str, Any], *, depth: int = 0) -> dict[str, Any]:
    if depth > 4:
        return {"_truncated": "max depth reached"}
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        lowered = key.lower()
        if lowered in SECRET_KEYS or "cookie" in lowered or "token" in lowered:
            sanitized[key] = "<redacted>"
        elif isinstance(value, Mapping):
            sanitized[key] = sanitize_mapping(value, depth=depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_mapping(item, depth=depth + 1) if isinstance(item, Mapping) else item
                for item in value[:20]
            ]
            if len(value) > 20:
                sanitized[f"{key}_truncated_count"] = len(value) - 20
        else:
            sanitized[key] = value
    return sanitized


def safe_json(data: Mapping[str, Any]) -> str:
    return truncate_rich_text(json.dumps(sanitize_mapping(data), ensure_ascii=True, default=str))


def truncate_rich_text(text: str | None, limit: int = MAX_RICH_TEXT) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    marker = "\n\n[truncated for Notion rich_text limit]"
    return text[: max(0, limit - len(marker))] + marker
