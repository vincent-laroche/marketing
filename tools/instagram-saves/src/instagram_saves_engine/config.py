from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .safety import redact


class Settings(BaseModel):
    notion_token: str | None = Field(default=None)
    notion_instagram_saves_database_id: str | None = Field(default=None)
    notion_content_ideas_database_id: str | None = Field(default=None)
    instagram_sessionid: str | None = Field(default=None)
    instagram_csrftoken: str | None = Field(default=None)
    instagram_ds_user_id: str | None = Field(default=None)
    instagram_mid: str | None = Field(default=None)
    instagram_ig_did: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    openai_model: str = "gpt-4.1-mini"
    sync_state_path: Path = Path("./data/sync_state.json")
    log_level: str = "INFO"
    content_factory_path: Path = Path("/Users/vincent/02_dev/content-factory")
    reel_enrichment_output_dir: Path = Path("./data/reel_enrichment")
    content_niche: str = "men's non-surgical hair replacement systems"
    content_pillars: list[str] = Field(
        default_factory=lambda: [
            "Education",
            "Trust",
            "Product Guidance",
            "Maintenance",
            "Objection Handling",
            "Founder POV",
            "Customer Journey",
        ]
    )
    instagram_collections: list[str] = Field(default_factory=list)

    @classmethod
    def load(cls, env_file: Path | None = None) -> Settings:
        local_env = env_file or Path.cwd() / ".env"
        if local_env.exists():
            load_dotenv(local_env)
        return cls(
            notion_token=os.getenv("NOTION_TOKEN"),
            notion_instagram_saves_database_id=os.getenv("NOTION_INSTAGRAM_SAVES_DATABASE_ID"),
            notion_content_ideas_database_id=os.getenv("NOTION_CONTENT_IDEAS_DATABASE_ID"),
            instagram_sessionid=os.getenv("INSTAGRAM_SESSIONID"),
            instagram_csrftoken=os.getenv("INSTAGRAM_CSRFTOKEN"),
            instagram_ds_user_id=os.getenv("INSTAGRAM_DS_USER_ID"),
            instagram_mid=os.getenv("INSTAGRAM_MID"),
            instagram_ig_did=os.getenv("INSTAGRAM_IG_DID"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            sync_state_path=Path(os.getenv("SYNC_STATE_PATH", "./data/sync_state.json")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            content_factory_path=Path(
                os.getenv("CONTENT_FACTORY_PATH", "/Users/vincent/02_dev/content-factory")
            ),
            reel_enrichment_output_dir=Path(
                os.getenv("REEL_ENRICHMENT_OUTPUT_DIR", "./data/reel_enrichment")
            ),
            content_niche=os.getenv(
                "CONTENT_NICHE", "men's non-surgical hair replacement systems"
            ),
            content_pillars=_split_csv(os.getenv("CONTENT_PILLARS")),
            instagram_collections=_split_csv(os.getenv("INSTAGRAM_COLLECTIONS")),
        )

    def missing_for_sync(self) -> list[str]:
        return _missing(
            {
                "NOTION_TOKEN": self.notion_token,
                "NOTION_INSTAGRAM_SAVES_DATABASE_ID": self.notion_instagram_saves_database_id,
                "INSTAGRAM_SESSIONID": self.instagram_sessionid,
                "INSTAGRAM_CSRFTOKEN": self.instagram_csrftoken,
                "INSTAGRAM_DS_USER_ID": self.instagram_ds_user_id,
            }
        )

    def missing_for_notion(self) -> list[str]:
        return _missing(
            {
                "NOTION_TOKEN": self.notion_token,
                "NOTION_INSTAGRAM_SAVES_DATABASE_ID": self.notion_instagram_saves_database_id,
                "NOTION_CONTENT_IDEAS_DATABASE_ID": self.notion_content_ideas_database_id,
            }
        )

    def missing_for_ideation(self) -> list[str]:
        return self.missing_for_notion() + _missing({"OPENAI_API_KEY": self.openai_api_key})

    def presence_report(self) -> dict[str, str]:
        values = {
            "NOTION_TOKEN": self.notion_token,
            "NOTION_INSTAGRAM_SAVES_DATABASE_ID": self.notion_instagram_saves_database_id,
            "NOTION_CONTENT_IDEAS_DATABASE_ID": self.notion_content_ideas_database_id,
            "INSTAGRAM_SESSIONID": self.instagram_sessionid,
            "INSTAGRAM_CSRFTOKEN": self.instagram_csrftoken,
            "INSTAGRAM_DS_USER_ID": self.instagram_ds_user_id,
            "INSTAGRAM_MID": self.instagram_mid,
            "INSTAGRAM_IG_DID": self.instagram_ig_did,
            "OPENAI_API_KEY": self.openai_api_key,
            "OPENAI_MODEL": self.openai_model,
            "SYNC_STATE_PATH": str(self.sync_state_path),
            "LOG_LEVEL": self.log_level,
            "CONTENT_FACTORY_PATH": str(self.content_factory_path),
            "REEL_ENRICHMENT_OUTPUT_DIR": str(self.reel_enrichment_output_dir),
        }
        return {key: redact(value) for key, value in values.items()}


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _missing(values: dict[str, str | None]) -> list[str]:
    return [key for key, value in values.items() if not value]
