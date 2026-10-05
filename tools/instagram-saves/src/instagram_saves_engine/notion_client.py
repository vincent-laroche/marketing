from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError

from .config import Settings
from .models import (
    ContentIdea,
    InstagramSave,
    MediaType,
    NotionInstagramSave,
    SaveStatus,
    parse_optional_url,
)
from .safety import safe_json, truncate_rich_text

INSTAGRAM_REQUIRED_PROPERTIES = {
    "Name",
    "Status",
    "Collection",
    "Caption",
    "Author",
    "Username",
    "Instagram URL",
    "Media ID",
    "Shortcode",
    "Type",
    "Saved At",
    "Synced At",
    "Last Seen At",
    "Source",
    "Raw JSON",
    "Processing Notes",
    "Content Idea Created",
    "Content Idea URL",
}

CONTENT_IDEA_REQUIRED_PROPERTIES = {
    "Name",
    "Status",
    "Priority",
    "Pillar",
    "Platform",
    "Format",
    "Angle",
    "Hook Options",
    "Outline",
    "CTA",
    "Script Draft",
    "Source Instagram URL",
    "Source Author",
    "Source Media ID",
    "Week Of",
    "Created From Save",
    "Created At",
    "Notes",
}

INSTAGRAM_ENRICHMENT_PROPERTIES = {
    "Audio Transcript",
    "On-Screen Text",
    "Combined Script",
    "Transcription Status",
    "OCR Status",
    "Source Extract JSON Path",
    "Extraction Notes",
}


class NotionClientError(RuntimeError):
    pass


def rich_text(value: str | None) -> list[dict[str, Any]]:
    text = truncate_rich_text(value)
    return [{"type": "text", "text": {"content": text}}] if text else []


def title(value: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": truncate_rich_text(value, 200)}}]


def select(value: str | None) -> dict[str, Any] | None:
    return {"name": value} if value else None


def date(value: datetime | None) -> dict[str, Any] | None:
    if not value:
        return None
    return {"start": value.isoformat()}


def instagram_save_properties(save: InstagramSave) -> dict[str, Any]:
    return {
        "Name": {"title": title(save.title)},
        "Status": {"select": select(SaveStatus.NEW.value)},
        "Collection": {"select": select(save.collection_name)},
        "Caption": {"rich_text": rich_text(save.caption)},
        "Author": {"rich_text": rich_text(save.author_display_name)},
        "Username": {"rich_text": rich_text(save.author_username)},
        "Instagram URL": {"url": parse_optional_url(save.url)},
        "Media ID": {"rich_text": rich_text(save.media_id)},
        "Shortcode": {"rich_text": rich_text(save.shortcode)},
        "Type": {"select": select(save.media_type.value)},
        "Saved At": {"date": date(save.saved_at)},
        "Synced At": {"date": date(save.synced_at)},
        "Last Seen At": {"date": date(datetime.now(UTC))},
        "Source": {"select": select("Instagram Saved")},
        "Raw JSON": {"rich_text": rich_text(safe_json(save.raw_json))},
        "Processing Notes": {"rich_text": []},
        "Content Idea Created": {"checkbox": False},
        "Content Idea URL": {"url": None},
    }


def content_idea_properties(idea: ContentIdea) -> dict[str, Any]:
    notes = idea.safety_notes
    if idea.production_notes:
        notes += f"\n\nProduction notes: {idea.production_notes}"
    if idea.claim_risk_flags:
        notes += "\n\nClaim-risk flags: " + ", ".join(idea.claim_risk_flags)
    return {
        "Name": {"title": title(idea.title)},
        "Status": {"select": select("Draft")},
        "Priority": {"select": select(idea.priority.value)},
        "Pillar": {"select": select(idea.pillar)},
        "Platform": {"multi_select": [{"name": platform} for platform in idea.platforms]},
        "Format": {"select": select(idea.format)},
        "Angle": {"rich_text": rich_text(idea.angle)},
        "Hook Options": {"rich_text": rich_text("\n".join(idea.hook_options))},
        "Outline": {"rich_text": rich_text(idea.outline)},
        "CTA": {"rich_text": rich_text(idea.cta)},
        "Script Draft": {"rich_text": rich_text(idea.script_draft)},
        "Source Instagram URL": {"url": parse_optional_url(idea.source_url)},
        "Source Author": {"rich_text": rich_text(idea.source_author)},
        "Source Media ID": {"rich_text": rich_text(idea.source_media_id)},
        "Week Of": {"date": None},
        "Created From Save": {"checkbox": True},
        "Created At": {"date": date(datetime.now(UTC))},
        "Notes": {"rich_text": rich_text(notes)},
    }


class NotionSavesClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.notion_token:
            raise NotionClientError("NOTION_TOKEN is missing")
        self.settings = settings
        self.client = Client(auth=settings.notion_token)
        self._instagram_saves_data_source_id: str | None = None
        self._content_ideas_data_source_id: str | None = None

    def validate_databases(self) -> dict[str, list[str]]:
        missing = self.settings.missing_for_notion()
        if missing:
            raise NotionClientError(f"Missing required Notion env vars: {', '.join(missing)}")
        assert self.settings.notion_instagram_saves_database_id
        assert self.settings.notion_content_ideas_database_id
        saves_db = self._retrieve_data_source(self._instagram_saves_source_id())
        ideas_db = self._retrieve_data_source(self._content_ideas_source_id())
        return {
            "instagram_saves_missing": sorted(
                INSTAGRAM_REQUIRED_PROPERTIES - set(saves_db.get("properties", {}).keys())
            ),
            "instagram_saves_enrichment_missing": sorted(
                INSTAGRAM_ENRICHMENT_PROPERTIES - set(saves_db.get("properties", {}).keys())
            ),
            "content_ideas_missing": sorted(
                CONTENT_IDEA_REQUIRED_PROPERTIES - set(ideas_db.get("properties", {}).keys())
            ),
        }

    def create_instagram_save(self, save: InstagramSave) -> str:
        response = self._request(
            self.client.pages.create,
            parent={"data_source_id": self._instagram_saves_source_id()},
            properties=instagram_save_properties(save),
        )
        return str(response["id"])

    def query_save_by_media(
        self, media_id: str, shortcode: str | None = None
    ) -> NotionInstagramSave | None:
        filters: list[dict[str, Any]] = [
            {"property": "Media ID", "rich_text": {"equals": media_id}}
        ]
        if shortcode:
            filters.append({"property": "Shortcode", "rich_text": {"equals": shortcode}})
        response = self._request(
            self.client.data_sources.query,
            data_source_id=self._instagram_saves_source_id(),
            filter={"or": filters},
            page_size=1,
        )
        results = response.get("results", [])
        return self._page_to_save(results[0]) if results else None

    def query_saves_by_status(
        self, status: SaveStatus = SaveStatus.NEW, limit: int = 25
    ) -> list[NotionInstagramSave]:
        response = self._request(
            self.client.data_sources.query,
            data_source_id=self._instagram_saves_source_id(),
            filter={"property": "Status", "select": {"equals": status.value}},
            page_size=min(limit, 100),
        )
        return [self._page_to_save(page) for page in response.get("results", [])]

    def query_reels_for_enrichment(self, limit: int = 10) -> list[NotionInstagramSave]:
        response = self._request(
            self.client.data_sources.query,
            data_source_id=self._instagram_saves_source_id(),
            filter={
                "and": [
                    {"property": "Type", "select": {"equals": MediaType.REEL.value}},
                    {
                        "or": [
                            {"property": "Transcription Status", "select": {"is_empty": True}},
                            {
                                "property": "Transcription Status",
                                "select": {"does_not_equal": "completed"},
                            },
                        ]
                    },
                ]
            },
            page_size=min(limit, 100),
        )
        return [self._page_to_save(page) for page in response.get("results", [])]

    def update_save_status(
        self,
        page_id: str,
        status: SaveStatus,
        *,
        processing_notes: str | None = None,
        content_idea_url: str | None = None,
    ) -> None:
        properties: dict[str, Any] = {"Status": {"select": select(status.value)}}
        if processing_notes is not None:
            properties["Processing Notes"] = {"rich_text": rich_text(processing_notes)}
        if content_idea_url is not None:
            properties["Content Idea Created"] = {"checkbox": True}
            properties["Content Idea URL"] = {"url": parse_optional_url(content_idea_url)}
        self._request(self.client.pages.update, page_id=page_id, properties=properties)

    def update_last_seen(self, page_id: str) -> None:
        self._request(
            self.client.pages.update,
            page_id=page_id,
            properties={"Last Seen At": {"date": date(datetime.now(UTC))}},
        )

    def update_save_enrichment(
        self,
        page_id: str,
        *,
        audio_transcript: str | None = None,
        on_screen_text: str | None = None,
        combined_script: str | None = None,
        transcription_status: str | None = None,
        ocr_status: str | None = None,
        source_extract_json_path: str | None = None,
        extraction_notes: str | None = None,
    ) -> None:
        properties: dict[str, Any] = {}
        if audio_transcript is not None:
            properties["Audio Transcript"] = {"rich_text": rich_text(audio_transcript)}
        if on_screen_text is not None:
            properties["On-Screen Text"] = {"rich_text": rich_text(on_screen_text)}
        if combined_script is not None:
            properties["Combined Script"] = {"rich_text": rich_text(combined_script)}
        if transcription_status is not None:
            properties["Transcription Status"] = {"select": select(transcription_status)}
        if ocr_status is not None:
            properties["OCR Status"] = {"select": select(ocr_status)}
        if source_extract_json_path is not None:
            properties["Source Extract JSON Path"] = {
                "rich_text": rich_text(source_extract_json_path)
            }
        if extraction_notes is not None:
            properties["Extraction Notes"] = {"rich_text": rich_text(extraction_notes)}
        if properties:
            self._request(self.client.pages.update, page_id=page_id, properties=properties)

    def create_content_idea(self, idea: ContentIdea) -> str:
        response = self._request(
            self.client.pages.create,
            parent={"data_source_id": self._content_ideas_source_id()},
            properties=content_idea_properties(idea),
        )
        return str(response["id"])

    def _retrieve_database(self, database_id: str) -> dict[str, Any]:
        return self._request(self.client.databases.retrieve, database_id=database_id)

    def _retrieve_data_source(self, data_source_id: str) -> dict[str, Any]:
        return self._request(self.client.data_sources.retrieve, data_source_id=data_source_id)

    def _first_data_source_id(self, database_id: str) -> str:
        database = self._retrieve_database(database_id)
        data_sources = database.get("data_sources") or []
        if not data_sources:
            if database.get("properties"):
                return database_id
            raise NotionClientError(
                f"Database {database_id} has no data source visible to this integration."
            )
        return str(data_sources[0]["id"])

    def _instagram_saves_source_id(self) -> str:
        if not self._instagram_saves_data_source_id:
            assert self.settings.notion_instagram_saves_database_id
            self._instagram_saves_data_source_id = self._first_data_source_id(
                self.settings.notion_instagram_saves_database_id
            )
        return self._instagram_saves_data_source_id

    def _content_ideas_source_id(self) -> str:
        if not self._content_ideas_data_source_id:
            assert self.settings.notion_content_ideas_database_id
            self._content_ideas_data_source_id = self._first_data_source_id(
                self.settings.notion_content_ideas_database_id
            )
        return self._content_ideas_data_source_id

    def _request(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except APIResponseError as exc:
            raise NotionClientError(
                f"Notion API error: {exc.code}. Check token, database sharing, and property names."
            ) from exc
        except Exception as exc:
            raise NotionClientError(f"Notion request failed: {exc}") from exc

    def _page_to_save(self, page: dict[str, Any]) -> NotionInstagramSave:
        props = page.get("properties", {})
        return NotionInstagramSave(
            page_id=page["id"],
            media_id=_rich_text_plain(props.get("Media ID")),
            shortcode=_rich_text_plain(props.get("Shortcode")),
            url=_url(props.get("Instagram URL")),
            author=_rich_text_plain(props.get("Username")) or _rich_text_plain(props.get("Author")),
            status=SaveStatus(_select_name(props.get("Status")) or SaveStatus.NEW.value),
            caption=_rich_text_plain(props.get("Caption")),
            collection_name=_select_name(props.get("Collection")),
            media_type=MediaType(_select_name(props.get("Type")) or MediaType.UNKNOWN.value),
            audio_transcript=_rich_text_plain(props.get("Audio Transcript")),
            on_screen_text=_rich_text_plain(props.get("On-Screen Text")),
            combined_script=_rich_text_plain(props.get("Combined Script")),
            transcription_status=_select_name(props.get("Transcription Status")),
            ocr_status=_select_name(props.get("OCR Status")),
        )


def _rich_text_plain(prop: dict[str, Any] | None) -> str | None:
    if not prop:
        return None
    chunks = prop.get("rich_text") or prop.get("title") or []
    text = "".join(chunk.get("plain_text", "") for chunk in chunks)
    return text or None


def _select_name(prop: dict[str, Any] | None) -> str | None:
    if not prop or not prop.get("select"):
        return None
    return prop["select"].get("name")


def _url(prop: dict[str, Any] | None) -> str | None:
    return prop.get("url") if prop else None
