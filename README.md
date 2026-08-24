# 노동법 블로그 → 워드프레스

원문 블로그 URL을 주면, `laws/` 폴더의 법령만 근거로 새 글을 쓰고 워드프레스에 올립니다.

## 준비

1. Python 3.10+
2. 이 폴더에서:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

3. `.env`에 OpenAI 키, 워드프레스 주소·사용자명·애플리케이션 비밀번호를 넣습니다.
4. 법령 파일을 `laws/`에 넣습니다. (`.txt` `.md` `.pdf`)

## 실행

웹페이지에서 주제·키워드·원문 글 URL을 넣으려면:

```bash
laborlaw serve
```

브라우저에서 http://127.0.0.1:8890 을 엽니다.

```bash
# 법령이 읽히는지 확인
laborlaw laws

# 업로드 없이 글만 생성
laborlaw run --topic "연차유급휴가" --keyword "연차유급휴가" --url "https://example.com/post" --dry-run

# 워드프레스에 올리기
laborlaw run --topic "연차유급휴가" --keyword "연차유급휴가" --url "https://example.com/post"
```

워드프레스 애플리케이션 비밀번호는 공백을 포함해도 됩니다. `.env`에는 따옴표 없이 그대로 넣으면 됩니다.

## GitHub / Vercel

저장소: https://github.com/reviewelio24-coder/laborlaw

Vercel에 연결한 뒤 환경 변수를 넣습니다.

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (`gpt-5.6`)
- `WP_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`
- `WP_STATUS`
- `WP_CATEGORY_NAME` (`노동법 쉽게 읽기`)

글 작성은 1~3분이 걸릴 수 있어, Vercel Hobby 요금제(약 10초 제한)에서는 `/api/run`이 끊길 수 있습니다. Pro에서 함수 제한 시간을 늘리는 것이 안전합니다.
