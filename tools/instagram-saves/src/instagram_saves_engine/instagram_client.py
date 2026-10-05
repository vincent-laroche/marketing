from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Settings
from .models import InstagramSave, MediaType
from .safety import sanitize_mapping

log = logging.getLogger(__name__)


class InstagramClientError(RuntimeError):
    pass


class InstagramClient:
    SAVED_FEED_URL = "https://www.instagram.com/api/v1/feed/saved/posts/"

    def __init__(self, settings: Settings, *, delay_seconds: float = 2.0) -> None:
        missing = [
            key
            for key, value in {
                "INSTAGRAM_SESSIONID": settings.instagram_sessionid,
                "INSTAGRAM_CSRFTOKEN": settings.instagram_csrftoken,
                "INSTAGRAM_DS_USER_ID": settings.instagram_ds_user_id,
            }.items()
            if not value
        ]
        if missing:
            raise InstagramClientError(f"Missing Instagram env vars: {', '.join(missing)}")
        self.settings = settings
        self.delay_seconds = delay_seconds
        self.client = httpx.Client(timeout=30.0, headers=self._headers(), cookies=self._cookies())

    def fetch_saved_posts(self, *, max_pages: int = 10) -> list[InstagramSave]:
        saves: list[InstagramSave] = []
        max_id: str | None = None
        for page in range(max_pages):
            params = {"max_id": max_id} if max_id else {}
            response = self.client.get(self.SAVED_FEED_URL, params=params)
            if response.status_code in {401, 403}:
                raise InstagramClientError(
                    "Instagram refused the request. Cookies may be expired or the account may "
                    "need browser review."
                )
            if response.status_code == 429:
                raise InstagramClientError(
                    "Instagram rate limited the request. Stop and retry later."
                )
            if response.status_code >= 400:
                raise InstagramClientError(
                    f"Instagram request failed with HTTP {response.status_code}."
                )
            data = response.json()
            if data.get("status") not in {None, "ok"}:
                raise InstagramClientError(
                    "Instagram returned a non-ok response. Stop instead of retrying aggressively."
                )
            items = data.get("items") or []
            log.info("Fetched Instagram saved page %s with %s items", page + 1, len(items))
            saves.extend(_parse_saved_items(items))
            more_available = bool(data.get("more_available"))
            max_id = data.get("next_max_id")
            if not more_available or not max_id:
                break
            time.sleep(self.delay_seconds)
        return saves

    def _headers(self) -> dict[str, str]:
        assert self.settings.instagram_csrftoken
        return {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.instagram.com/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "x-csrftoken": self.settings.instagram_csrftoken,
            "x-ig-app-id": "936619743392459",
            "x-requested-with": "XMLHttpRequest",
        }

    def _cookies(self) -> dict[str, str]:
        cookies = {
            "sessionid": self.settings.instagram_sessionid,
            "csrftoken": self.settings.instagram_csrftoken,
            "ds_user_id": self.settings.instagram_ds_user_id,
            "mid": self.settings.instagram_mid,
            "ig_did": self.settings.instagram_ig_did,
        }
        return {key: value for key, value in cookies.items() if value}


def _parse_saved_items(items: list[dict[str, Any]]) -> list[InstagramSave]:
    saves: list[InstagramSave] = []
    for item in items:
        media = item.get("media") or item
        media_id = str(media.get("id") or media.get("pk") or "")
        if not media_id:
            continue
        shortcode = media.get("code") or media.get("shortcode")
        user = media.get("user") or {}
        caption_obj = media.get("caption") or {}
        caption = caption_obj.get("text") if isinstance(caption_obj, dict) else None
        collection = _collection_name(item)
        saves.append(
            InstagramSave(
                media_id=media_id,
                shortcode=shortcode,
                url=f"https://www.instagram.com/p/{shortcode}/" if shortcode else None,
                author_username=user.get("username"),
                author_display_name=user.get("full_name"),
                caption=caption,
                media_type=_media_type(media),
                collection_name=collection,
                saved_at=_saved_at(item),
                raw_json=sanitize_mapping(
                    {
                        "media": {
                            "id": media.get("id"),
                            "pk": media.get("pk"),
                            "code": shortcode,
                            "media_type": media.get("media_type"),
                            "product_type": media.get("product_type"),
                            "user": {
                                "username": user.get("username"),
                                "full_name": user.get("full_name"),
                            },
                        },
                        "collection": collection,
                    }
                ),
            )
        )
    return saves


def _media_type(media: dict[str, Any]) -> MediaType:
    product_type = str(media.get("product_type") or "").lower()
    if product_type in {"clips", "reels", "igtv"}:
        return MediaType.REEL if product_type != "igtv" else MediaType.IGTV
    media_type = str(media.get("media_type") or "").lower()
    if media_type in {"1", "image", "photo"}:
        return MediaType.POST
    if media_type in {"2", "video"}:
        return MediaType.REEL
    if media_type in {"8", "carousel", "album"}:
        return MediaType.CAROUSEL
    return MediaType.UNKNOWN


def _collection_name(item: dict[str, Any]) -> str | None:
    for key in ("collection", "collection_metadata", "saved_collection"):
        value = item.get(key)
        if isinstance(value, dict):
            name = value.get("collection_name") or value.get("name") or value.get("title")
            if name:
                return str(name)
    return None


def _saved_at(item: dict[str, Any]) -> datetime | None:
    raw = item.get("taken_at") or item.get("saved_at") or item.get("created_at")
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(float(raw), tz=UTC)
    except (TypeError, ValueError):
        return None
