from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration for the application."""

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    data_dir: Path = Field(Path("data"), alias="DATA_DIR")
    chat_model: str = Field("gpt-4o-mini", alias="CHAT_MODEL")
    serve_docs: bool = Field(True, alias="SERVE_DOCS")
    docs_mount_path: str = Field("/docs", alias="DOCS_MOUNT_PATH")
    allowed_origins: list[str] = Field(["*"], alias="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=(".env", "config/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir

    def ensure_env(self) -> None:
        os.environ.setdefault("OPENAI_API_KEY", self.openai_api_key)
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_env()
    return settings
