from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Settings
from .enrich import run_reel_enrichment
from .ideate import IdeationError, generate_content_ideas
from .logging_config import configure_logging
from .models import NotionInstagramSave, SaveStatus
from .notion_client import NotionClientError, NotionSavesClient
from .state import StateManager
from .sync import run_sync

app = typer.Typer(no_args_is_help=True)
console = Console()


def _settings() -> Settings:
    settings = Settings.load()
    configure_logging(settings.log_level)
    return settings


@app.command("validate-config")
def validate_config() -> None:
    settings = _settings()
    table = Table(title="Configuration")
    table.add_column("Variable")
    table.add_column("Status")
    for key, value in settings.presence_report().items():
        table.add_row(key, value)
    console.print(table)
    sync_missing = settings.missing_for_sync()
    notion_missing = settings.missing_for_notion()
    if sync_missing or notion_missing:
        console.print("[yellow]Missing values are expected until .env is configured.[/yellow]")
    else:
        console.print("[green]Required sync and Notion values are present.[/green]")


@app.command("validate-notion")
def validate_notion() -> None:
    settings = _settings()
    try:
        result = NotionSavesClient(settings).validate_databases()
    except NotionClientError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    for key, missing in result.items():
        if missing:
            console.print(f"[red]{key}: missing {', '.join(missing)}[/red]")
        else:
            console.print(f"[green]{key}: all required properties found[/green]")
    if any(result.values()):
        raise typer.Exit(1)


@app.command("sync")
def sync_command() -> None:
    settings = _settings()
    try:
        summary = run_sync(settings)
    except Exception as exc:
        console.print(f"[red]Sync failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print_json(summary.model_dump_json())


@app.command("list-new")
def list_new(limit: Annotated[int, typer.Option(help="Maximum rows to show")] = 25) -> None:
    settings = _settings()
    saves = NotionSavesClient(settings).query_saves_by_status(SaveStatus.NEW, limit=limit)
    _print_saves(saves)


@app.command("mark-reviewed")
def mark_reviewed(page_ids: Annotated[list[str] | None, typer.Argument()] = None) -> None:
    settings = _settings()
    notion = NotionSavesClient(settings)
    ids = page_ids or []
    if not ids:
        saves = notion.query_saves_by_status(SaveStatus.NEW, limit=50)
        _print_saves(saves)
        raw = typer.prompt("Enter page numbers or Notion page IDs to mark Reviewed")
        ids = _resolve_selection(raw, saves)
    for page_id in ids:
        notion.update_save_status(page_id, SaveStatus.REVIEWED)
        console.print(f"[green]Marked Reviewed:[/green] {page_id}")


@app.command("show-state")
def show_state() -> None:
    settings = _settings()
    manager = StateManager(settings.sync_state_path)
    console.print_json(json.dumps(manager.summary(), indent=2))


@app.command("enrich-reels")
def enrich_reels(
    limit: Annotated[int, typer.Option(help="Maximum reels to enrich")] = 3,
    dry_run: Annotated[bool, typer.Option(help="List candidates without transcribing")] = False,
) -> None:
    settings = _settings()
    missing = settings.missing_for_sync()
    if missing:
        console.print(f"[red]Missing required Instagram env vars: {', '.join(missing)}[/red]")
        raise typer.Exit(1)
    try:
        summary = run_reel_enrichment(settings, limit=limit, dry_run=dry_run)
    except Exception as exc:
        console.print(f"[red]Reel enrichment failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print_json(json.dumps(summary.as_dict(), indent=2))


@app.command("ideate")
def ideate(limit: Annotated[int, typer.Option(help="Maximum new saves to review")] = 20) -> None:
    settings = _settings()
    if not settings.openai_api_key:
        console.print(
            "[yellow]OPENAI_API_KEY is missing. Sync works, but ideation requires it.[/yellow]"
        )
        raise typer.Exit(1)
    notion = NotionSavesClient(settings)
    saves = notion.query_saves_by_status(SaveStatus.NEW, limit=limit)
    if not saves:
        console.print("[green]No New saves found.[/green]")
        return
    _print_saves(saves)
    raw = typer.prompt("Process all, selected numbers/IDs, or skip? [all/1,3/skip]", default="skip")
    if raw.strip().lower() in {"skip", "s", "none"}:
        return
    selected = saves if raw.strip().lower() == "all" else [
        save for save in saves if save.page_id in _resolve_selection(raw, saves)
    ]
    for save in selected:
        try:
            ideas = generate_content_ideas(settings, save)
        except IdeationError as exc:
            console.print(f"[red]{exc}[/red]")
            continue
        for idea in ideas:
            console.print(Panel(_idea_preview(idea), title=idea.title))
            action = typer.prompt(
                "approve, approve edited title, reject, skip, mark source as reviewed, or quit",
                default="skip",
            ).strip().lower()
            if action == "quit":
                raise typer.Exit()
            if action == "approve edited title":
                idea.title = typer.prompt("Edited title", default=idea.title)
                action = "approve"
            if action == "approve":
                page_id = notion.create_content_idea(idea)
                notion.update_save_status(
                    save.page_id,
                    SaveStatus.PROCESSED,
                    processing_notes="Content idea created from manual ideation review.",
                    content_idea_url=f"https://www.notion.so/{page_id.replace('-', '')}",
                )
                console.print(f"[green]Created idea and marked source Processed:[/green] {page_id}")
            elif action == "reject":
                reject_action = typer.prompt(
                    "Mark source Reviewed or leave New? [reviewed/new]", default="reviewed"
                )
                if reject_action.strip().lower().startswith("review"):
                    notion.update_save_status(save.page_id, SaveStatus.REVIEWED)
            elif action == "mark source as reviewed":
                notion.update_save_status(save.page_id, SaveStatus.REVIEWED)


def _print_saves(saves: list[NotionInstagramSave]) -> None:
    table = Table(title="New Instagram Saves")
    table.add_column("#")
    table.add_column("Page ID")
    table.add_column("Author")
    table.add_column("Type")
    table.add_column("Collection")
    table.add_column("Caption Preview")
    table.add_column("URL")
    for index, save in enumerate(saves, start=1):
        table.add_row(
            str(index),
            save.page_id,
            save.author or "",
            save.media_type.value,
            save.collection_name or "",
            (save.caption or "")[:120],
            save.url or "",
        )
    console.print(table)


def _resolve_selection(raw: str, saves: list[NotionInstagramSave]) -> list[str]:
    selected: list[str] = []
    by_index = {str(index): save.page_id for index, save in enumerate(saves, start=1)}
    for item in [part.strip() for part in raw.split(",") if part.strip()]:
        selected.append(by_index.get(item, item))
    return selected


def _idea_preview(idea: object) -> str:
    data = idea.model_dump()  # type: ignore[attr-defined]
    return "\n".join(
        [
            f"Pillar: {data['pillar']}",
            f"Priority: {data['priority']}",
            f"Platforms: {', '.join(data['platforms'])}",
            f"Format: {data['format']}",
            f"Angle: {data['angle']}",
            "Hooks:",
            *[f"- {hook}" for hook in data["hook_options"]],
            f"Outline: {data['outline']}",
            f"CTA: {data['cta']}",
            f"Safety notes: {data['safety_notes']}",
        ]
    )


if __name__ == "__main__":
    app()
