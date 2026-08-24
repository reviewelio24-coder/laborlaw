from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
LAWS_DIR = ROOT / "laws"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    wp_url: str
    wp_username: str
    wp_app_password: str
    wp_status: str
    wp_category_ids: list[int]
    wp_category_name: str
    wp_tag_ids: list[int]
    article_min_chars: int
    laws_dir: Path


def _ids(raw: str) -> list[int]:
    if not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    wp_url = os.getenv("WP_URL", "").strip().rstrip("/")
    wp_user = os.getenv("WP_USERNAME", "").strip()
    wp_pass = os.getenv("WP_APP_PASSWORD", "").strip()
    missing = []
    if not key:
        missing.append("OPENAI_API_KEY")
    if not wp_url:
        missing.append("WP_URL")
    if not wp_user:
        missing.append("WP_USERNAME")
    if not wp_pass:
        missing.append("WP_APP_PASSWORD")
    if missing:
        raise ConfigError(
            "다음 환경변수가 없습니다. .env 파일을 채우세요: " + ", ".join(missing)
        )
    status = os.getenv("WP_STATUS", "draft").strip().lower()
    if status not in {"draft", "publish", "pending"}:
        raise ConfigError("WP_STATUS는 draft, publish, pending 중 하나여야 합니다.")
    return Settings(
        openai_api_key=key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6").strip() or "gpt-5.6",
        wp_url=wp_url,
        wp_username=wp_user,
        wp_app_password=wp_pass,
        wp_status=status,
        wp_category_ids=_ids(os.getenv("WP_CATEGORY_IDS", "")),
        wp_category_name=os.getenv("WP_CATEGORY_NAME", "노동법 쉽게 읽기").strip()
        or "노동법 쉽게 읽기",
        wp_tag_ids=_ids(os.getenv("WP_TAG_IDS", "")),
        article_min_chars=int(os.getenv("ARTICLE_MIN_CHARS", "2500")),
        laws_dir=LAWS_DIR,
    )
