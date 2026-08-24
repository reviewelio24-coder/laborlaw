from __future__ import annotations

import json

from laborlaw.config import ROOT, load_settings
from laborlaw.fetch_source import fetch_source
from laborlaw.generate import ArticleJob, InsufficientSourceError, generate_article
from laborlaw.laws import format_law_context, load_law_chunks, retrieve_relevant
from laborlaw.wordpress import publish_post

_chunk_cache: list | None = None
_chunk_mtime: float | None = None


def law_chunks_cached():
    global _chunk_cache, _chunk_mtime
    settings = load_settings()
    mtimes = [
        p.stat().st_mtime
        for p in settings.laws_dir.iterdir()
        if p.is_file() and not p.name.startswith("._")
    ]
    stamp = max(mtimes) if mtimes else 0.0
    if _chunk_cache is None or _chunk_mtime != stamp:
        _chunk_cache = load_law_chunks(settings.laws_dir)
        _chunk_mtime = stamp
    return _chunk_cache


def run_pipeline(
    topic: str,
    keyword: str,
    url: str = "",
    extra: str = "",
    dry_run: bool = False,
) -> dict:
    topic = topic.strip()
    keyword = keyword.strip()
    if not topic or not keyword:
        raise ValueError("주제와 메인 키워드를 입력하세요.")
    settings = load_settings()
    chunks = law_chunks_cached()
    source = fetch_source(url) if url.strip() else None
    query = "\n".join(
        x
        for x in (
            topic,
            keyword,
            extra,
            (source.title + "\n" + source.text) if source else "",
        )
        if x
    )
    relevant = retrieve_relevant(chunks, query)
    law_context = format_law_context(relevant)
    try:
        article = generate_article(
            settings,
            ArticleJob(topic=topic, keyword=keyword, extra=extra, source=source),
            law_context,
        )
    except InsufficientSourceError as exc:
        return {
            "insufficient": True,
            "missing": str(exc),
            "title": "",
            "excerpt": "",
            "html": "",
            "source_title": source.title if source else "",
            "source_url": source.url if source else "",
            "law_chunks": len(relevant),
            "dry_run": True,
            "wp_id": None,
            "wp_status": None,
            "wp_link": None,
            "saved_path": None,
            "core_keywords": [],
            "related_keywords": [],
            "hashtags": [],
            "meta_description": "",
            "meta_char_count": 0,
        }
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    dump = out_dir / "last_article.json"
    dump.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "insufficient": False,
        "missing": "",
        "title": article["title"],
        "excerpt": article["excerpt"],
        "html": article["html"],
        "source_title": source.title if source else "",
        "source_url": source.url if source else "",
        "law_chunks": len(relevant),
        "dry_run": dry_run,
        "wp_id": None,
        "wp_status": None,
        "wp_link": None,
        "saved_path": str(dump),
        "core_keywords": article["core_keywords"],
        "related_keywords": article["related_keywords"],
        "hashtags": article["hashtags"],
        "meta_description": article.get("meta_description", ""),
        "meta_char_count": article.get("meta_char_count", 0),
    }
    if dry_run:
        return result
    posted = publish_post(
        settings,
        article["title"],
        article["html"],
        article.get("meta_description") or article["excerpt"],
        tag_names=article["hashtags"],
        meta_description=article.get("meta_description") or "",
    )
    link = posted.get("link") or posted.get("guid", {}).get("rendered")
    result["wp_id"] = posted.get("id")
    result["wp_status"] = posted.get("status")
    result["wp_link"] = link
    return result
