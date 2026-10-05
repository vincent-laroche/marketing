from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .models import NotionInstagramSave
from .notion_client import NotionSavesClient


class EnrichmentError(RuntimeError):
    pass


@dataclass
class EnrichmentSummary:
    candidates: int = 0
    enriched: int = 0
    skipped: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "candidates": self.candidates,
            "enriched": self.enriched,
            "skipped": self.skipped,
            "errors": self.errors,
        }


def run_reel_enrichment(
    settings: Settings, *, limit: int = 3, dry_run: bool = False
) -> EnrichmentSummary:
    notion = NotionSavesClient(settings)
    saves = notion.query_reels_for_enrichment(limit=limit)
    summary = EnrichmentSummary(candidates=len(saves))
    settings.reel_enrichment_output_dir.mkdir(parents=True, exist_ok=True)

    for save in saves:
        if not save.url or not save.shortcode:
            summary.skipped += 1
            continue
        if dry_run:
            summary.skipped += 1
            continue
        try:
            result = transcribe_reel(settings, save)
            transcript = (result.get("text") or "").strip()
            combined = "\n\n".join(
                part for part in [save.caption or "", transcript, save.on_screen_text or ""] if part
            )
            extract_path = write_enrichment_record(settings, save, result, combined)
            notion.update_save_enrichment(
                save.page_id,
                audio_transcript=transcript,
                combined_script=combined,
                transcription_status="completed" if transcript else "empty",
                ocr_status=save.ocr_status or "pending",
                source_extract_json_path=str(extract_path),
                extraction_notes=(
                    "Audio transcript generated via content-factory reel transcriber bridge."
                ),
            )
            summary.enriched += 1
        except Exception as exc:
            notion.update_save_enrichment(
                save.page_id,
                transcription_status="error",
                extraction_notes=f"Reel enrichment failed: {str(exc)[:500]}",
            )
            summary.errors += 1
    return summary


def transcribe_reel(settings: Settings, save: NotionInstagramSave) -> dict[str, str]:
    bridge = Path(__file__).resolve().parents[2] / "scripts" / "transcribe_reel_bridge.js"
    if not bridge.exists():
        raise EnrichmentError(f"Missing bridge script: {bridge}")
    if not settings.content_factory_path.exists():
        raise EnrichmentError(f"Missing content-factory path: {settings.content_factory_path}")

    cookie_file = write_yt_dlp_cookie_file(settings)
    env = os.environ.copy()
    env["YT_DLP_COOKIES_FILE"] = str(cookie_file)
    venv_bin = Path(__file__).resolve().parents[2] / ".venv" / "bin"
    if venv_bin.exists():
        env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    payload = {
        "content_factory_path": str(settings.content_factory_path),
        "url": save.url,
        "shortcode": save.shortcode,
        "account_id": (save.author or "saved").replace("@", "") or "saved",
        "timeout_ms": 300000,
    }
    completed = subprocess.run(
        ["node", str(bridge), json.dumps(payload)],
        check=False,
        capture_output=True,
        text=True,
        timeout=330,
        env=env,
    )
    if completed.returncode != 0:
        message = completed.stderr or completed.stdout or "transcription failed"
        raise EnrichmentError(message.strip())
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise EnrichmentError("transcriber returned invalid JSON") from exc


def write_yt_dlp_cookie_file(settings: Settings) -> Path:
    cookie_path = settings.reel_enrichment_output_dir / "instagram.cookies.txt"
    rows = [
        "# Netscape HTTP Cookie File",
        _cookie_row("sessionid", settings.instagram_sessionid),
        _cookie_row("csrftoken", settings.instagram_csrftoken),
        _cookie_row("ds_user_id", settings.instagram_ds_user_id),
        _cookie_row("mid", settings.instagram_mid),
        _cookie_row("ig_did", settings.instagram_ig_did),
    ]
    cookie_path.write_text("\n".join(row for row in rows if row) + "\n", encoding="utf-8")
    cookie_path.chmod(0o600)
    return cookie_path


def _cookie_row(name: str, value: str | None) -> str:
    if not value:
        return ""
    return f".instagram.com\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}"


def write_enrichment_record(
    settings: Settings, save: NotionInstagramSave, result: dict[str, str], combined: str
) -> Path:
    shortcode = save.shortcode or save.media_id or save.page_id
    path = settings.reel_enrichment_output_dir / f"{shortcode}.json"
    path.write_text(
        json.dumps(
            {
                "source": {
                    "page_id": save.page_id,
                    "url": save.url,
                    "shortcode": save.shortcode,
                    "media_id": save.media_id,
                    "author": save.author,
                },
                "transcription": result,
                "combined_script": combined,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
