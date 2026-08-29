from __future__ import annotations

from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from laborlaw.auth import (
    AuthGateMiddleware,
    SESSION_COOKIE,
    credentials_match,
    https_only,
    load_auth,
)
from laborlaw.config import ConfigError, load_settings
from laborlaw.pipeline import run_pipeline

STATIC = Path(__file__).resolve().parent / "static"
_run_lock = Lock()


class RunRequest(BaseModel):
    topic: str = Field(min_length=1)
    keyword: str = Field(min_length=1)
    url: str = ""
    refs: list[str] = Field(default_factory=list)
    extra: str = ""
    dry_run: bool = False


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


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

    @app.get("/favicon.ico")
    def favicon():
        return FileResponse(STATIC / "favicon.ico")

    @app.get("/login")
    def login_page():
        return FileResponse(STATIC / "login.html")

    @app.post("/api/login")
    def login(body: LoginRequest, request: Request):
        cfg = load_auth()
        if cfg is None:
            raise HTTPException(
                status_code=503,
                detail="AUTH_USERNAME, AUTH_PASSWORD 환경변수를 설정하세요.",
            )
        if not credentials_match(body.username.strip(), body.password, cfg):
            raise HTTPException(
                status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다."
            )
        request.session.clear()
        request.session["user"] = cfg.username
        return {"ok": True}

    @app.post("/api/logout")
    def logout(request: Request):
        request.session.clear()
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
        refs: list[str] = []
        seen = {url} if url else set()
        for raw in body.refs:
            ref = _normalize_url(raw)
            if not ref or ref in seen:
                continue
            seen.add(ref)
            refs.append(ref)
        if len(refs) > 10:
            raise HTTPException(status_code=400, detail="참고 URL은 최대 10개까지 넣을 수 있습니다.")
        if not _run_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409, detail="이미 글을 작성 중입니다. 끝날 때까지 기다려 주세요."
            )
        try:
            return run_pipeline(
                topic=body.topic,
                keyword=body.keyword,
                url=url,
                refs=refs,
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

    auth = load_auth()
    app.add_middleware(AuthGateMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=(auth.secret if auth else "laborlaw-unconfigured"),
        session_cookie=SESSION_COOKIE,
        same_site="lax",
        https_only=https_only(),
        max_age=60 * 60 * 24 * 30,
    )
    return app


app = create_app()
