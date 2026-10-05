from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from .config import Settings
from .models import ContentIdea, NotionInstagramSave

DEFAULT_IDEATION_INSTRUCTION = (
    "You are transforming a saved Instagram post into content ideas for Hair Solutions Co., "
    "a premium DTC ecommerce brand selling men's non-surgical hair replacement systems. "
    "Reframe the source concept without copying the original creator. Preserve only the strategic "
    "idea, format insight, or content mechanic. Create original angles suitable for a trust-heavy "
    "category. Avoid medical claims, miracle claims, shame-based language, fake urgency, or "
    "unrealistic transformation promises."
)


class IdeationError(RuntimeError):
    pass


def generate_content_ideas(settings: Settings, save: NotionInstagramSave) -> list[ContentIdea]:
    if not settings.openai_api_key:
        raise IdeationError("OPENAI_API_KEY is missing. Sync still works, but ideation needs it.")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": DEFAULT_IDEATION_INSTRUCTION,
            },
            {
                "role": "user",
                "content": _prompt(settings, save),
            },
        ],
        response_format={"type": "json_object"},
    )
    raw_text = response.choices[0].message.content or ""
    try:
        data = json.loads(raw_text)
        ideas = data.get("ideas", data if isinstance(data, list) else [])
        return [ContentIdea.model_validate(_with_source(idea, save)) for idea in ideas]
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise IdeationError(f"OpenAI returned an invalid content idea object: {exc}") from exc


def _prompt(settings: Settings, save: NotionInstagramSave) -> str:
    return json.dumps(
        {
            "task": "Create one structured content idea from this saved Instagram item.",
            "output_contract": {
                "ideas": [
                    {
                        "title": "string",
                        "pillar": "one configured pillar",
                        "priority": "High|Medium|Low",
                        "platforms": ["Instagram", "TikTok", "YouTube Shorts"],
                        "format": (
                            "Reel|Carousel|Short Video|Long-form Video|Static Post|Story|Email|Blog"
                        ),
                        "angle": "string",
                        "hook_options": ["string", "string", "string"],
                        "outline": "string",
                        "cta": "string",
                        "script_draft": "string",
                        "source_url": "string or null",
                        "source_author": "string or null",
                        "source_media_id": "string or null",
                        "safety_notes": "string",
                        "production_notes": "string",
                        "claim_risk_flags": ["string"],
                    }
                ]
            },
            "brand_context": {
                "business": "Hair Solutions Co.",
                "niche": settings.content_niche,
                "pillars": settings.content_pillars,
                "guardrails": [
                    "No medical claims",
                    "No miracle hair loss promises",
                    "No guaranteed transformation claims",
                    "No manipulative insecurity-based copy",
                    "No refund, replacement, shipping, policy, pricing, or clinical-result claims",
                    "Do not copy the original creator's wording",
                ],
            },
            "source_save": save.model_dump(mode="json"),
        },
        ensure_ascii=True,
    )


def _with_source(idea: dict[str, Any], save: NotionInstagramSave) -> dict[str, Any]:
    merged = dict(idea)
    merged.setdefault("source_url", save.url)
    merged.setdefault("source_author", save.author)
    merged.setdefault("source_media_id", save.media_id)
    return merged
