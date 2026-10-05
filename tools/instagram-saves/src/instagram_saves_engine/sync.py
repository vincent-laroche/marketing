from __future__ import annotations

import logging

from .config import Settings
from .instagram_client import InstagramClient
from .models import SyncSummary
from .notion_client import NotionSavesClient
from .state import StateManager

log = logging.getLogger(__name__)


def run_sync(settings: Settings) -> SyncSummary:
    missing = settings.missing_for_sync()
    if missing:
        raise RuntimeError(f"Missing required sync env vars: {', '.join(missing)}")

    state = StateManager(settings.sync_state_path)
    instagram = InstagramClient(settings)
    notion = NotionSavesClient(settings)
    summary = SyncSummary()

    try:
        saves = instagram.fetch_saved_posts()
        summary.fetched_count = len(saves)
        for save in saves:
            if state.has_seen(save.media_id, save.shortcode):
                existing = notion.query_save_by_media(save.media_id, save.shortcode)
                if existing:
                    notion.update_last_seen(existing.page_id)
                    summary.updated_count += 1
                summary.skipped_duplicate_count += 1
                state.mark_seen(save.media_id, shortcode=save.shortcode)
                continue

            existing = notion.query_save_by_media(save.media_id, save.shortcode)
            if existing:
                notion.update_last_seen(existing.page_id)
                state.mark_seen(
                    save.media_id, shortcode=save.shortcode, notion_page_id=existing.page_id
                )
                summary.skipped_duplicate_count += 1
                summary.updated_count += 1
                continue

            try:
                page_id = notion.create_instagram_save(save)
                state.mark_seen(save.media_id, shortcode=save.shortcode, notion_page_id=page_id)
                summary.created_count += 1
            except Exception:
                summary.error_count += 1
                log.exception("Failed to create Notion page for media_id=%s", save.media_id)
        state.mark_success()
        return summary
    except Exception as exc:
        state.mark_error(str(exc))
        raise
    finally:
        state.save()
