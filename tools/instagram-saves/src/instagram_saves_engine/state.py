from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .models import now_iso


class SeenMedia(BaseModel):
    media_id: str
    shortcode: str | None = None
    notion_page_id: str | None = None
    first_seen_at: str = Field(default_factory=now_iso)
    last_seen_at: str = Field(default_factory=now_iso)


class SyncState(BaseModel):
    seen_media: dict[str, SeenMedia] = Field(default_factory=dict)
    shortcode_index: dict[str, str] = Field(default_factory=dict)
    last_successful_sync_at: str | None = None
    last_error: str | None = None


class StateManager:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.state = self.load()

    def load(self) -> SyncState:
        if not self.path.exists():
            return SyncState()
        with self.path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
        return SyncState.model_validate(data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.state.model_dump(mode="json"), file, indent=2, sort_keys=True)

    def has_seen(self, media_id: str | None, shortcode: str | None = None) -> bool:
        if media_id and media_id in self.state.seen_media:
            return True
        return bool(shortcode and shortcode in self.state.shortcode_index)

    def mark_seen(
        self,
        media_id: str,
        *,
        shortcode: str | None = None,
        notion_page_id: str | None = None,
    ) -> None:
        existing = self.state.seen_media.get(media_id)
        if existing:
            existing.last_seen_at = now_iso()
            if notion_page_id:
                existing.notion_page_id = notion_page_id
            if shortcode:
                existing.shortcode = shortcode
        else:
            self.state.seen_media[media_id] = SeenMedia(
                media_id=media_id, shortcode=shortcode, notion_page_id=notion_page_id
            )
        if shortcode:
            self.state.shortcode_index[shortcode] = media_id

    def mark_success(self) -> None:
        self.state.last_successful_sync_at = now_iso()
        self.state.last_error = None

    def mark_error(self, message: str) -> None:
        self.state.last_error = message[:500]

    def summary(self) -> dict[str, str | int | None]:
        return {
            "state_path": str(self.path),
            "seen_media_count": len(self.state.seen_media),
            "shortcode_count": len(self.state.shortcode_index),
            "last_successful_sync_at": self.state.last_successful_sync_at,
            "last_error": self.state.last_error,
        }
