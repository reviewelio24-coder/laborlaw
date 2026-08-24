from __future__ import annotations

from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from laborlaw.config import ConfigError, load_settings
from laborlaw.pipeline import run_pipeline

STATIC = Path(__file__).resolve().parent / "static"
_run_lock = Lock()


class RunRequest(BaseModel):
    topic: str = Field(min_length=1)
    keyword: str = Field(min_length=1)
    url: str = ""
    extra: str = ""
    dry_run: bool = False


def _normalize_url(raw: str) -> str:
    url = raw.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="올바른 웹 주소가 아닙니다.")
    return url


def create_app() -> FastAPI:
    app = FastAPI(title="노동법 글 작성")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/status")
    def status():
        try:
            settings = load_settings()
        except ConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {
            "wp_url": settings.wp_url,
            "wp_status": settings.wp_status,
            "model": settings.openai_model,
        }

    @app.post("/api/run")
    def run(body: RunRequest):
        url = _normalize_url(body.url)
        if not _run_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409, detail="이미 글을 작성 중입니다. 끝날 때까지 기다려 주세요."
            )
        try:
            return run_pipeline(
                topic=body.topic,
                keyword=body.keyword,
                url=url,
                extra=body.extra,
                dry_run=body.dry_run,
            )
        except ConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            _run_lock.release()

    return app


app = create_app()
