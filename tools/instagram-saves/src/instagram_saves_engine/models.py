from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class MediaType(StrEnum):
    POST = "Post"
    REEL = "Reel"
    CAROUSEL = "Carousel"
    IGTV = "IGTV"
    UNKNOWN = "Unknown"


class SaveStatus(StrEnum):
    NEW = "New"
    REVIEWED = "Reviewed"
    PROCESSED = "Processed"
    SKIPPED = "Skipped"
    ERROR = "Error"


class ContentPriority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ContentIdeaStatus(StrEnum):
    DRAFT = "Draft"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    IN_PRODUCTION = "In Production"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


class InstagramSave(BaseModel):
    media_id: str
    shortcode: str | None = None
    url: str | None = None
    author_username: str | None = None
    author_display_name: str | None = None
    caption: str | None = None
    media_type: MediaType = MediaType.UNKNOWN
    collection_name: str | None = None
    saved_at: datetime | None = None
    synced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("media_type", mode="before")
    @classmethod
    def normalize_media_type(cls, value: Any) -> MediaType:
        if isinstance(value, MediaType):
            return value
        if value is None:
            return MediaType.UNKNOWN
        normalized = str(value).strip().lower()
        if normalized in {"1", "image", "photo", "post", "feed"}:
            return MediaType.POST
        if normalized in {"2", "video", "reel", "clips", "clip"}:
            return MediaType.REEL
        if normalized in {"8", "carousel", "album", "sidecar"}:
            return MediaType.CAROUSEL
        if normalized == "igtv":
            return MediaType.IGTV
        return MediaType.UNKNOWN

    @property
    def title(self) -> str:
        author = self.author_username or self.author_display_name or "Instagram save"
        label = self.shortcode or self.media_id
        return f"{author} - {label}"


class NotionInstagramSave(BaseModel):
    page_id: str
    media_id: str | None = None
    shortcode: str | None = None
    url: str | None = None
    author: str | None = None
    status: SaveStatus = SaveStatus.NEW
    caption: str | None = None
    collection_name: str | None = None
    media_type: MediaType = MediaType.UNKNOWN
    audio_transcript: str | None = None
    on_screen_text: str | None = None
    combined_script: str | None = None
    transcription_status: str | None = None
    ocr_status: str | None = None


class ContentIdea(BaseModel):
    title: str
    pillar: str
    priority: ContentPriority = ContentPriority.MEDIUM
    platforms: list[str]
    format: str
    angle: str
    hook_options: list[str]
    outline: str
    cta: str
    script_draft: str
    source_url: str | None = None
    source_author: str | None = None
    source_media_id: str | None = None
    safety_notes: str
    production_notes: str | None = None
    claim_risk_flags: list[str] = Field(default_factory=list)

    @field_validator("hook_options")
    @classmethod
    def require_hooks(cls, value: list[str]) -> list[str]:
        if len(value) < 3:
            raise ValueError("content ideas require at least 3 hook options")
        return value


class SyncSummary(BaseModel):
    fetched_count: int = 0
    created_count: int = 0
    skipped_duplicate_count: int = 0
    updated_count: int = 0
    error_count: int = 0


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_optional_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(HttpUrl(value))
    except Exception:
        return value
