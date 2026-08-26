const form = document.getElementById("form");
const topicInput = document.getElementById("topic");
const keywordInput = document.getElementById("keyword");
const urlInput = document.getElementById("url");
const extraInput = document.getElementById("extra");
const dryInput = document.getElementById("dry");
const addRefBtn = document.getElementById("add-ref");
const refUrlsEl = document.getElementById("ref-urls");
const submit = document.getElementById("submit");
const metaDesc = document.getElementById("meta-desc");
const metaCount = document.getElementById("meta-count");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const metaEl = document.getElementById("meta");

function show(el, html, className) {
  el.className = className;
  el.innerHTML = html;
}

function noSpaceLen(text) {
  return String(text).replace(/\s+/g, "").length;
}

function setMetaDescription(text) {
  const value = text || "";
  metaDesc.value = value;
  const n = noSpaceLen(value);
  const ok = n >= 100 && n <= 110;
  metaCount.textContent = `공백 제외 ${n}자${value ? (ok ? " (적합)" : " (100~110자 권장)") : ""}`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "설정을 읽지 못했습니다.");
    metaEl.textContent = `발행 대상 ${data.wp_url} · 상태 ${data.wp_status} · 모델 ${data.model}`;
  } catch (err) {
    metaEl.textContent = err.message;
  }
}

function collectRefUrls() {
  return [...refUrlsEl.querySelectorAll(".ref-url")]
    .map((el) => el.value.trim())
    .filter(Boolean);
}

function addRefInput() {
  if (refUrlsEl.querySelectorAll(".ref-url").length >= 10) {
    return;
  }
  const index = refUrlsEl.querySelectorAll(".ref-url").length;
  const input = document.createElement("input");
  input.className = "ref-url";
  input.type = "url";
  input.inputMode = "url";
  input.autocomplete = "off";
  input.placeholder = "https://example.com/reference";
  input.id = `ref-url-${index}`;
  refUrlsEl.appendChild(input);
  input.focus();
}

addRefBtn.addEventListener("click", addRefInput);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultEl.className = "result hidden";
  setMetaDescription("");
  submit.disabled = true;
  show(
    statusEl,
    "허용 소스와 법령을 확인한 뒤 글을 작성합니다. 1~3분 걸릴 수 있습니다.",
    "status busy"
  );
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: topicInput.value.trim(),
        keyword: keywordInput.value.trim(),
        url: urlInput.value.trim(),
        refs: collectRefUrls(),
        extra: extraInput.value.trim(),
        dry_run: dryInput.checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((x) => x.msg || x).join(" ")
        : data.detail || "실패했습니다.";
      throw new Error(detail);
    }
    statusEl.className = "status hidden";
    if (data.insufficient) {
      show(
        resultEl,
        `<strong>자료를 더 넣어 주세요</strong><p>${escapeHtml(data.missing)}</p>`,
        "result err"
      );
      return;
    }
    setMetaDescription(data.meta_description || "");
    const link = data.wp_link
      ? `<p>워드프레스: <a href="${data.wp_link}" target="_blank" rel="noopener">${data.wp_link}</a> (ID ${data.wp_id}, ${data.wp_status})</p>`
      : "<p>워드프레스에는 올리지 않았습니다. 초안만 저장했습니다.</p>";
    const tags = (data.hashtags || []).map((t) => `#${t}`).join(" ");
    show(
      resultEl,
      `<strong>${escapeHtml(data.title)}</strong>
       <p>핵심 키워드: ${escapeHtml((data.core_keywords || []).join(", "))}</p>
       <p>연관 키워드: ${escapeHtml((data.related_keywords || []).join(", "))}</p>
       <p>${escapeHtml(tags)}</p>
       ${link}
       <p>참조 조문 ${data.law_chunks}개</p>
       <p>메타 설명 (공백 제외 ${data.meta_char_count || 0}자)</p>
       <div class="preview">${data.html}</div>`,
      "result ok"
    );
  } catch (err) {
    statusEl.className = "status hidden";
    show(resultEl, err.message, "result err");
  } finally {
    submit.disabled = false;
  }
});

loadStatus();
