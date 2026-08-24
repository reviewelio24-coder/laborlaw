from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".txt", ".md", ".pdf"}
ARTICLE_SPLIT = re.compile(r"(?=제\s*\d+\s*조(?:의\s*\d+)?)")


@dataclass
class LawChunk:
    statute: str
    heading: str
    text: str
    source_file: str


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _chunks_from_text(statute: str, source_file: str, raw: str) -> list[LawChunk]:
    cleaned = re.sub(r"\r\n?", "\n", raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    pieces = [p.strip() for p in ARTICLE_SPLIT.split(cleaned) if p.strip()]
    chunks: list[LawChunk] = []
    if len(pieces) <= 1:
        for i in range(0, len(cleaned), 1800):
            block = cleaned[i : i + 1800].strip()
            if block:
                chunks.append(
                    LawChunk(
                        statute=statute,
                        heading=f"{statute} 발췌",
                        text=block,
                        source_file=source_file,
                    )
                )
        return chunks
    for piece in pieces:
        first = piece.split("\n", 1)[0][:80]
        chunks.append(
            LawChunk(
                statute=statute,
                heading=first,
                text=piece[:4000],
                source_file=source_file,
            )
        )
    return chunks


def load_law_chunks(laws_dir: Path) -> list[LawChunk]:
    files = sorted(
        p
        for p in laws_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in SUPPORTED
        and p.name != "README.md"
        and not p.name.startswith("._")
    )
    if not files:
        raise RuntimeError(
            f"법령 파일이 없습니다. {laws_dir} 에 .txt, .md, .pdf 를 넣으세요."
        )
    chunks: list[LawChunk] = []
    for path in files:
        statute = path.stem
        text = _read_file(path)
        if not text.strip():
            continue
        chunks.extend(_chunks_from_text(statute, path.name, text))
    if not chunks:
        raise RuntimeError("법령 파일에서 조문을 읽지 못했습니다.")
    return chunks


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[가-힣A-Za-z0-9]{2,}", text.lower()))


def retrieve_relevant(
    chunks: list[LawChunk], query: str, limit: int = 18
) -> list[LawChunk]:
    q = _tokens(query)
    scored: list[tuple[float, LawChunk]] = []
    for chunk in chunks:
        c = _tokens(chunk.text)
        if not c:
            continue
        overlap = len(q & c)
        if overlap == 0:
            continue
        score = overlap / (1 + abs(len(c) - 80) / 200)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [item[1] for item in scored[:limit]]
    if len(picked) < 8:
        picked = chunks[: min(limit, len(chunks))]
    return picked


def format_law_context(chunks: list[LawChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, 1):
        blocks.append(
            f"[{i}] 법령파일={chunk.source_file} / {chunk.heading}\n{chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)
