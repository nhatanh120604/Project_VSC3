from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Annotated, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .deps import get_app_settings, get_service
from .service import PoetryChefService
from .schemas import AskRequest, AskResponse
from .settings import Settings

import logging



LOGGER = logging.getLogger(__name__)
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


settings = get_app_settings()

app = FastAPI(
    title="Poetry Chef Assistant",
    docs_url="/swagger",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mount_static_docs(settings: Settings) -> None:
    if not settings.serve_docs:
        return
    doc_dir: Path = settings.resolved_data_dir
    if not doc_dir.exists():
        return
    mount_path = settings.docs_mount_path.rstrip("/") or "/docs"
    already_mounted = any(
        getattr(route, "path", None) == mount_path for route in app.routes
    )
    if already_mounted:
        return
    app.mount(
        mount_path, StaticFiles(directory=str(doc_dir), check_dir=False), name="docs"
    )


_mount_static_docs(settings)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse, tags=["assistant"])
async def ask_endpoint(
    payload: AskRequest,
    service: Annotated[PoetryChefService, Depends(get_service)],
) -> AskResponse:
    start_ts = perf_counter()
    result = service.ask(
        question=payload.question,
        additional_context=payload.additional_context,
        temperature=payload.temperature,
    )
    duration = perf_counter() - start_ts

    LOGGER.info(
        "Ask request completed in %.3fs for emotion: %s",
        duration,
        payload.question
    )
    return AskResponse.from_chain_result(
        answer=result["answer"],
        citations=result["citations"],
        sources=result["sources"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
