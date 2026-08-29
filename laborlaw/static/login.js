const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const submit = document.getElementById("submit");
const errorEl = document.getElementById("error");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorEl.className = "result err hidden";
  submit.disabled = true;
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((x) => x.msg || x).join(" ")
        : data.detail || "로그인에 실패했습니다.";
      throw new Error(detail);
    }
    window.location.href = "/";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.className = "result err";
  } finally {
    submit.disabled = false;
  }
});
