from __future__ import annotations

from functools import lru_cache

from .service import PoetryChefService
from .settings import Settings, get_settings


@lru_cache()
def get_service() -> PoetryChefService:
    settings = get_settings()
    return PoetryChefService(settings)


def get_app_settings() -> Settings:
    return get_settings()
