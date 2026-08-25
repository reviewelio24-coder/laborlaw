from __future__ import annotations

from typing import Any

import requests

from laborlaw.config import Settings

DEFAULT_CATEGORY = "노동법 쉽게 읽기"


def publish_post(
    settings: Settings,
    title: str,
    html: str,
    excerpt: str,
    tag_names: list[str] | None = None,
    meta_description: str = "",
    focus_keyword: str = "",
) -> dict[str, Any]:
    auth = (settings.wp_username, settings.wp_app_password)
    headers = {"Content-Type": "application/json"}
    category_ids = list(settings.wp_category_ids)
    category_name = settings.wp_category_name or DEFAULT_CATEGORY
    cat_id = _ensure_term(settings, "categories", category_name)
    if cat_id not in category_ids:
        category_ids.append(cat_id)
    tag_ids = list(settings.wp_tag_ids)
    for name in tag_names or []:
        cleaned = name.strip().lstrip("#")
        if not cleaned:
            continue
        tid = _ensure_term(settings, "tags", cleaned)
        if tid not in tag_ids:
            tag_ids.append(tid)
    payload: dict[str, Any] = {
        "title": title,
        "content": html,
        "excerpt": excerpt,
        "status": settings.wp_status,
        "categories": category_ids,
    }
    if tag_ids:
        payload["tags"] = tag_ids
    seo_meta = _seo_meta(meta_description, focus_keyword)
    if meta_description:
        payload["excerpt"] = meta_description
    if seo_meta:
        payload["meta"] = seo_meta
    response = requests.post(
        f"{settings.wp_url}/wp-json/wp/v2/posts",
        json=payload,
        auth=auth,
        headers=headers,
        timeout=60,
    )
    if response.status_code >= 400 and "meta" in payload:
        payload.pop("meta", None)
        response = requests.post(
            f"{settings.wp_url}/wp-json/wp/v2/posts",
            json=payload,
            auth=auth,
            headers=headers,
            timeout=60,
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"워드프레스 업로드 실패 ({response.status_code}): {response.text[:800]}"
        )
    return response.json()


def _seo_meta(meta_description: str, focus_keyword: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    desc = meta_description.strip()
    focus = focus_keyword.strip()
    if desc:
        meta["_yoast_wpseo_metadesc"] = desc
        meta["rank_math_description"] = desc
    if focus:
        meta["_yoast_wpseo_focuskw"] = focus
        meta["_yoast_wpseo_focuskw_text_input"] = focus
        meta["rank_math_focus_keyword"] = focus
    return meta


def _ensure_term(settings: Settings, taxonomy: str, name: str) -> int:
    auth = (settings.wp_username, settings.wp_app_password)
    base = f"{settings.wp_url}/wp-json/wp/v2/{taxonomy}"
    found = requests.get(
        base,
        params={"search": name, "per_page": 100},
        auth=auth,
        timeout=30,
    )
    if found.status_code < 400:
        for item in found.json():
            if str(item.get("name", "")).strip() == name:
                return int(item["id"])
    created = requests.post(
        base,
        json={"name": name},
        auth=auth,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if created.status_code < 400:
        return int(created.json()["id"])
    data = created.json() if created.headers.get("Content-Type", "").startswith("application/json") else {}
    existing = data.get("data", {}).get("term_id") if isinstance(data, dict) else None
    if existing:
        return int(existing)
    raise RuntimeError(
        f"워드프레스 {taxonomy} '{name}' 처리 실패 ({created.status_code}): {created.text[:500]}"
    )
