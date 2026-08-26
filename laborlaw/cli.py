from __future__ import annotations

import argparse

from laborlaw.config import ConfigError
from laborlaw.pipeline import run_pipeline
from laborlaw.laws import load_law_chunks


def cmd_run(
    topic: str,
    keyword: str,
    url: str,
    extra: str,
    dry_run: bool,
    refs: list[str] | None = None,
) -> None:
    try:
        result = run_pipeline(
            topic=topic,
            keyword=keyword,
            url=url,
            extra=extra,
            dry_run=dry_run,
            refs=refs or [],
        )
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc
    if result.get("insufficient"):
        raise SystemExit(result["missing"])
    print(f"제목: {result['title']}")
    print(f"원문: {result['source_url']}")
    print(f"참조 조문 조각: {result['law_chunks']}개")
    print(f"초안 저장: {result['saved_path']}")
    if result["core_keywords"]:
        print("핵심 키워드: " + ", ".join(result["core_keywords"]))
    if result["dry_run"]:
        print("dry-run: 워드프레스에 올리지 않았습니다.")
        return
    print(f"워드프레스 ID: {result['wp_id']}  상태: {result['wp_status']}")
    print(f"글 주소: {result['wp_link']}")


def cmd_list_laws() -> None:
    from laborlaw.config import LAWS_DIR

    try:
        chunks = load_law_chunks(LAWS_DIR)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    files = sorted({c.source_file for c in chunks})
    print(f"법령 폴더: {LAWS_DIR}")
    print(f"파일 {len(files)}개, 조문 조각 {len(chunks)}개")
    for name in files:
        n = sum(1 for c in chunks if c.source_file == name)
        print(f"  - {name} ({n})")


def cmd_serve(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run("laborlaw.web:app", host=host, port=port, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="노동법 근거 새 글 작성 후 워드프레스 업로드"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="글을 만들고 업로드")
    run.add_argument("--topic", required=True, help="작성할 노동법 주제")
    run.add_argument("--keyword", required=True, help="SEO 메인 키워드")
    run.add_argument("--url", default="", help="원문 글 URL (선택)")
    run.add_argument("--ref", action="append", default=[], help="참고 URL (여러 번 지정 가능)")
    run.add_argument("--extra", default="", help="추가 요구사항 (선택)")
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="워드프레스에 올리지 않고 output/last_article.json만 저장",
    )
    sub.add_parser("laws", help="로드된 법령 파일 목록")
    serve = sub.add_parser("serve", help="입력 웹페이지 실행")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8890)
    args = parser.parse_args()
    if args.cmd == "run":
        cmd_run(args.topic, args.keyword, args.url, args.extra, args.dry_run, args.ref)
    elif args.cmd == "laws":
        cmd_list_laws()
    elif args.cmd == "serve":
        cmd_serve(args.host, args.port)


if __name__ == "__main__":
    main()
