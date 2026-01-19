function formatTime(sec) {
  const s = Math.max(0, Math.floor(sec));
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  const pad = (n) => (n < 10 ? "0" + n : "" + n);
  return (hrs ? pad(hrs) + ":" : "") + pad(mins) + ":" + pad(secs);
}

document.addEventListener("DOMContentLoaded", () => {
  const timerEls = document.querySelectorAll(".bs-timer");
  for (const timerEl of timerEls) {
    const base = parseInt(timerEl.getAttribute("data-elapsed") || "0", 10);
    if (Number.isNaN(base)) continue;

    const isLive = timerEl.getAttribute("data-live") === "1";

    let counter = base;
    timerEl.textContent = formatTime(counter);

    if (isLive) {
      setInterval(() => {
        counter += 1;
        timerEl.textContent = formatTime(counter);
      }, 1000);
    }
  }

  // Start page preferences panel toggle.
  const prefsEl = document.querySelector(".bs-start-prefs");
  const prefsToggleEl = document.querySelector(".bs-prefs-toggle");
  if (prefsEl && prefsToggleEl) {
    prefsToggleEl.addEventListener("click", () => {
      const collapsed = prefsEl.classList.toggle("is-collapsed");
      prefsToggleEl.setAttribute("aria-expanded", collapsed ? "false" : "true");
      prefsToggleEl.textContent = collapsed ? "›" : "‹";
    });
  }

  const quizShellEl = document.querySelector(".bs-quiz-shell");
  const showAnswers = quizShellEl && quizShellEl.getAttribute("data-show-answers") === "1";
  const gradeUrl = quizShellEl ? quizShellEl.getAttribute("data-grade-url") : null;

  function isQuestionAnswered(cardEl) {
    const inputs = cardEl.querySelectorAll("input, textarea");
    for (const el of inputs) {
      if (el.tagName === "TEXTAREA") {
        if ((el.value || "").trim().length > 0) return true;
        continue;
      }

      if (el.type === "checkbox" || el.type === "radio") {
        if (el.checked) return true;
        continue;
      }

      if ((el.value || "").trim().length > 0) return true;
    }
    return false;
  }

  function extractAnswer(cardEl) {
    const multi = cardEl.querySelectorAll('input[type="checkbox"][name^="answer_multi_"]');
    if (multi.length) {
      const letters = [];
      for (const el of multi) {
        if (el.checked) letters.push(el.value);
      }
      return letters.join(",");
    }

    const radio = cardEl.querySelector('input[type="radio"][name^="answer_"]:checked');
    if (radio) return radio.value;

    const textarea = cardEl.querySelector('textarea[name^="answer_"]');
    if (textarea) return (textarea.value || "").trim();

    const input = cardEl.querySelector(
      'input[name^="answer_"]:not([type="radio"]):not([type="checkbox"])'
    );
    if (input) return (input.value || "").trim();

    return "";
  }

  function clearStatusClasses(tile) {
    tile.classList.remove("is-correct", "is-partial", "is-incorrect");
  }

  async function requestGrade(idx, answer) {
    if (!gradeUrl) return null;

    const res = await fetch(gradeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: idx, answer }),
    });

    if (!res.ok) return null;
    const data = await res.json();
    return data.status || null;
  }

  const gradeTimers = new Map();

  async function updateSidebarForCard(cardEl) {
    const id = cardEl.getAttribute("id") || "";
    const match = id.match(/^q-(\d+)$/);
    if (!match) return;

    const qIndex = match[1];
    const tile = document.querySelector(`.bs-nav-tile[data-question-index="${qIndex}"]`);
    if (!tile) return;

    tile.classList.toggle("is-answered", isQuestionAnswered(cardEl));

    if (!showAnswers) return;

    const answer = extractAnswer(cardEl);
    if (!answer) {
      clearStatusClasses(tile);
      return;
    }

    // Debounce grading requests while the user is typing.
    const existing = gradeTimers.get(qIndex);
    if (existing) clearTimeout(existing);

    gradeTimers.set(
      qIndex,
      setTimeout(async () => {
        const status = await requestGrade(parseInt(qIndex, 10), answer);
        clearStatusClasses(tile);
        if (status) tile.classList.add(`is-${status}`);
      }, 200)
    );
  }

  const questionCards = document.querySelectorAll(".bs-question-card");
  for (const cardEl of questionCards) {
    const handler = () => void updateSidebarForCard(cardEl);

    handler();

    cardEl.addEventListener("change", handler);
    cardEl.addEventListener("input", handler);
  }
});
