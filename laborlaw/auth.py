from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from laborlaw.config import ROOT

SESSION_COOKIE = "laborlaw_session"
PUBLIC_PATHS = frozenset(
    {"/login", "/api/login", "/api/logout", "/health", "/favicon.ico"}
)


@dataclass(frozen=True)
class AuthConfig:
    username: str
    password: str
    secret: str


_cached: AuthConfig | None | bool = False


def load_auth() -> AuthConfig | None:
    global _cached
    if _cached is not False:
        return _cached
    load_dotenv(ROOT / ".env")
    username = os.getenv("AUTH_USERNAME", "").strip()
    password = os.getenv("AUTH_PASSWORD", "").strip()
    if not username or not password:
        _cached = None
        return None
    secret = os.getenv("AUTH_SECRET", "").strip()
    if not secret:
        secret = hashlib.sha256(
            f"laborlaw|{username}|{password}".encode()
        ).hexdigest()
    _cached = AuthConfig(username=username, password=password, secret=secret)
    return _cached


def https_only() -> bool:
    return bool(os.getenv("VERCEL"))


def credentials_match(username: str, password: str, cfg: AuthConfig) -> bool:
    user_ok = hmac.compare_digest(username, cfg.username)
    pass_ok = hmac.compare_digest(password, cfg.password)
    return user_ok and pass_ok


class AuthGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/static/"):
            return await call_next(request)
        if load_auth() is None:
            if path.startswith("/api/"):
                return JSONResponse(
                    {
                        "detail": "AUTH_USERNAME, AUTH_PASSWORD 환경변수를 설정하세요."
                    },
                    status_code=503,
                )
            return RedirectResponse("/login", status_code=302)
        if request.session.get("user"):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse(
                {"detail": "로그인이 필요합니다."}, status_code=401
            )
        return RedirectResponse("/login", status_code=302)
