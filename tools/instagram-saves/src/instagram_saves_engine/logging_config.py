from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler


def configure_logging(level: str = "INFO", *, log_file: Path | None = None) -> None:
    handlers: list[logging.Handler] = [RichHandler(rich_tracebacks=False, show_path=False)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("notion_client").setLevel(logging.WARNING)
