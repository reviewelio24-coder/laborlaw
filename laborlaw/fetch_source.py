from __future__ import annotations

from dataclasses import dataclass

import requests
import trafilatura
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LaborLawBlogBot/0.1; +https://local)"
    )
}


@dataclass
class SourceArticle:
    url: str
    title: str
    text: str
    excerpt: str


def fetch_source(url: str, timeout: int = 30) -> SourceArticle:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"원문 페이지를 가져오지 못했습니다. 주소를 확인하세요. ({exc})") from exc
    html = response.text
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
        url=url,
    )
    soup = BeautifulSoup(html, "lxml")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = str(og["content"]).strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    text = (extracted or "").strip()
    if not text:
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
    if len(text) < 200:
        raise RuntimeError("본문을 충분히 추출하지 못했습니다. URL을 확인하세요.")
    excerpt = text[:400].replace("\n", " ")
    return SourceArticle(url=url, title=title or url, text=text, excerpt=excerpt)
