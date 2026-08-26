from __future__ import annotations

import json
import re
from dataclasses import dataclass

from openai import OpenAI

from laborlaw.config import Settings
from laborlaw.editor_prompt import SYSTEM_PROMPT
from laborlaw.fetch_source import SourceArticle


@dataclass
class ArticleJob:
    topic: str
    keyword: str
    extra: str = ""
    source: SourceArticle | None = None
    references: list[SourceArticle] | None = None


def generate_article(
    settings: Settings,
    job: ArticleJob,
    law_context: str,
) -> dict:
    client = OpenAI(api_key=settings.openai_api_key)
    source_block = "(원문 글 URL 없음. SOURCE B 없음. SOURCE A 첨부 법령만 허용 소스입니다.)"
    if job.source:
        source_block = f"""원문 글 URL: {job.source.url}
원문 제목: {job.source.title}

[SOURCE B — 원문 글 본문]
{job.source.text[:12000]}"""
    refs = job.references or []
    if refs:
        ref_blocks = []
        for i, ref in enumerate(refs, 1):
            ref_blocks.append(
                f"""참고 URL {i}: {ref.url}
제목: {ref.title}

[SOURCE C — 참고 글 {i} 본문]
{ref.text[:8000]}"""
            )
        ref_block = "\n\n".join(ref_blocks)
    else:
        ref_block = "(참고 URL 없음. SOURCE C 없음.)"
    extra = job.extra.strip() or "(없음)"
    user = f"""주제: {job.topic}
메인 키워드: {job.keyword}
원문 글 URL: {job.source.url if job.source else "(없음)"}
참고 URL: {", ".join(ref.url for ref in refs) or "(없음)"}
추가 요구사항: {extra}

[SOURCE B — 원문 글]
{source_block}

[SOURCE C — 참고 URL]
{ref_block}

[SOURCE A — 첨부 법조문]
{law_context}

법조문 직접 인용은 SOURCE A에서만 하세요. SOURCE B·C의 조문이 SOURCE A에서 확인되지 않으면 직접 인용하지 마세요.

이 글은 WordPress 카테고리 「노동법 쉽게 읽기」에 게시됩니다. 본문에 카테고리명을 쓰지 마세요.
해시태그 10개는 hashtags 배열에만 넣고 본문 HTML에 #태그를 넣지 마세요. 프로그램이 WordPress 태그란에 넣습니다.
메타 설명은 meta_description 필드에만 넣으세요. 공백 제외 100~110자, 메인 키워드 1회, 글의 핵심만 요약하세요.
서론의 첫 단락(첫 <p>)에 메인 키워드를 반드시 포함하세요.
"""
    kwargs = {
        "model": settings.openai_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }
    if settings.openai_model.startswith("gpt-5"):
        kwargs["max_completion_tokens"] = 8000
    else:
        kwargs["temperature"] = 0.3
        kwargs["max_tokens"] = 8000
    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    if bool(data.get("insufficient")):
        missing = str(data.get("missing") or "").strip()
        conflict = str(data.get("conflict") or "").strip()
        parts = [p for p in (missing, conflict) if p]
        raise InsufficientSourceError(
            " ".join(parts)
            or "제공된 자료만으로는 이 부분을 정확하게 작성하기 어렵습니다."
        )
    title = str(data.get("title", "")).strip()
    excerpt = str(data.get("excerpt", "")).strip()
    html = _strip_hashtag_block(_sanitize_html(str(data.get("html", "")).strip()))
    if not title or not html:
        raise RuntimeError("GPT가 제목 또는 본문을 반환하지 않았습니다.")
    core = _list(data.get("core_keywords"), 5)
    related = _list(data.get("related_keywords"), 10)
    tags = [t.lstrip("#") for t in _list(data.get("hashtags"), 10)]
    meta_description = str(data.get("meta_description") or "").strip()
    footer = _footer_html(core, related)
    return {
        "title": title,
        "excerpt": excerpt[:200],
        "meta_description": meta_description,
        "html": html + footer,
        "core_keywords": core,
        "related_keywords": related,
        "hashtags": tags,
        "counts": data.get("counts") or {},
        "main_keyword_count": data.get("main_keyword_count"),
        "meta_char_count": _no_space_len(meta_description),
    }


class InsufficientSourceError(RuntimeError):
    pass


def _no_space_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _list(value, size: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(x).strip() for x in value if str(x).strip()]
    return items[:size]


def _footer_html(core: list[str], related: list[str]) -> str:
    parts = []
    if core:
        parts.append(f"<p><strong>핵심 키워드:</strong> {', '.join(core)}</p>")
    if related:
        parts.append(f"<p><strong>연관 키워드:</strong> {', '.join(related)}</p>")
    if not parts:
        return ""
    return "<h2>키워드</h2>\n" + "\n".join(parts)


def _strip_hashtag_block(html: str) -> str:
    html = re.sub(
        r"<h2>[^<]*해시태그[^<]*</h2>\s*(?:<p>.*?</p>\s*)?",
        "",
        html,
        flags=re.I | re.S,
    )
    html = re.sub(r"<p>\s*(?:#[^\s<]+\s*){3,}</p>", "", html, flags=re.I)
    return html


def _sanitize_html(html: str) -> str:
    allowed = {"h2", "h3", "p", "ul", "ol", "li", "blockquote", "strong", "em", "br"}
    html = re.sub(r"</?(script|style|iframe)[^>]*>", "", html, flags=re.I)

    def repl(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        if tag not in allowed:
            return ""
        return match.group(0)

    return re.sub(r"</?([a-zA-Z0-9]+)([^>]*)>", repl, html)
