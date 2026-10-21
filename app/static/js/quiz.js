(function () {
  "use strict";

  // ─────────────────────────────────────────────────────────────────────
  // Shared helpers
  // ─────────────────────────────────────────────────────────────────────

  function formatTime(sec) {
    const s = Math.max(0, Math.floor(sec));
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    const pad = (n) => (n < 10 ? "0" + n : "" + n);
    return (hrs ? pad(hrs) + ":" : "") + pad(mins) + ":" + pad(secs);
  }

  function storeKey(quizId) {
    return "quiz-ui:attempt:" + quizId;
  }

  function readStored(quizId) {
    try {
      const raw = localStorage.getItem(storeKey(quizId));
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || typeof data !== "object" || data.version !== 1) return null;
      return data;
    } catch (e) {
      return null;
    }
  }

  function writeStored(quizId, data) {
    try {
      localStorage.setItem(storeKey(quizId), JSON.stringify(data));
    } catch (e) {
      /* storage unavailable (private mode etc.) — autosave to server still works */
    }
  }

  function clearStored(quizId) {
    try {
      localStorage.removeItem(storeKey(quizId));
    } catch (e) {
      /* ignore */
    }
  }

  function isoNow() {
    return new Date().toISOString();
  }

  function plural(n, unit) {
    return n + " " + unit + (n === 1 ? "" : "s");
  }

  function relativeAgo(iso) {
    const t = Date.parse(iso || "");
    if (Number.isNaN(t)) return "";
    const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 60) return "less than a minute";
    const mins = Math.floor(s / 60);
    if (mins < 60) return plural(mins, "minute");
    const hours = Math.floor(mins / 60);
    if (hours < 24) return plural(hours, "hour");
    const days = Math.floor(hours / 24);
    if (days < 7) return plural(days, "day");
    return plural(Math.floor(days / 7), "week");
  }

  function timeNewer(aIso, bIso) {
    const a = Date.parse(aIso || "");
    const b = Date.parse(bIso || "");
    if (Number.isNaN(a)) return false;
    if (Number.isNaN(b)) return true;
    return a > b;
  }

  async function postJson(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      /* non-JSON response */
    }
    return { status: res.status, ok: res.ok, data: data };
  }

  // ─────────────────────────────────────────────────────────────────────
  // Quiz page
  // ─────────────────────────────────────────────────────────────────────

  function initQuizPage() {
    const shell = document.querySelector(".bs-quiz-shell");
    if (!shell) return;

    const quizId = shell.dataset.quizId || "";
    const hasAttempt = shell.dataset.hasAttempt === "1";
    const stateUrl = shell.dataset.stateUrl || "";
    const answerUrl = shell.dataset.answerUrl || "";
    const timerUrl = shell.dataset.timerUrl || "";
    const settingsUrl = shell.dataset.settingsUrl || "";
    const startUrl = shell.dataset.startUrl || "/";

    let local = readStored(quizId);

    // If the server has no in-progress attempt (fresh visit or server
    // restart), restore from localStorage when possible, else bounce to
    // the start page.
    if (!hasAttempt) {
      if (local && local.quiz_id === quizId && !local.submitted) {
        pushFullState().then((res) => {
          if (res && res.ok) window.location.reload();
          else window.location.replace(startUrl);
        });
      } else {
        window.location.replace(startUrl);
      }
      return;
    }

    // ── timer engine ──────────────────────────────────────────────────

    const limitRaw = shell.dataset.limitSeconds;
    let limitSeconds = parseInt(limitRaw || "", 10);
    const isCountdown = !Number.isNaN(limitSeconds);
    if (!isCountdown) limitSeconds = null;

    let elapsed = parseInt(shell.dataset.elapsedSeconds || "0", 10);
    if (Number.isNaN(elapsed)) elapsed = 0;
    let paused = shell.dataset.paused === "1";

    const timerEl = shell.querySelector(".bs-timer");
    const timerCopyEl = shell.querySelector(".bs-quiz-timer-copy");
    const timerWrap = shell.querySelector(".bs-timer-wrap");
    const timerToggleBtn = shell.querySelector(".bs-timer-hover-toggle");

    let showAnswers = shell.dataset.showAnswers === "1";

    function renderTimer() {
      if (timerEl) {
        timerEl.textContent = isCountdown
          ? formatTime(Math.max(0, limitSeconds - elapsed))
          : formatTime(elapsed);
      }
      if (timerCopyEl) {
        timerCopyEl.textContent =
          (isCountdown ? "remaining" : "elapsed") + (paused ? " (paused)" : "");
      }
      if (timerToggleBtn) {
        timerToggleBtn.textContent = paused ? "\u25B6" : "\u23F8";
        timerToggleBtn.setAttribute("aria-label", paused ? "Resume timer" : "Pause timer");
      }
      const settingsToggleBtn = shell.querySelector(".bs-timer-toggle-btn");
      if (settingsToggleBtn) {
        settingsToggleBtn.textContent = paused ? "Resume" : "Pause";
        settingsToggleBtn.dataset.timerAction = paused ? "resume" : "pause";
      }
    }

    // ── local persistence ──────────────────────────────────────────────

    function ensureLocal() {
      if (!local) {
        local = {
          version: 1,
          quiz_id: quizId,
          attempt_id: shell.dataset.attemptId || "",
          answers: {},
          show_answers_in_sidebar: showAnswers,
          timer: {
            mode: isCountdown ? "countdown" : "stopwatch",
            limit_seconds: limitSeconds,
            elapsed_seconds: elapsed,
            paused: paused,
          },
          attempt_started_at: shell.dataset.startedAt || isoNow(),
          last_saved_at: shell.dataset.serverSavedAt || isoNow(),
          submitted: false,
        };
      }
    }

    function persistLocal() {
      ensureLocal();
      local.quiz_id = quizId;
      local.show_answers_in_sidebar = showAnswers;
      local.timer = {
        mode: isCountdown ? "countdown" : "stopwatch",
        limit_seconds: limitSeconds,
        elapsed_seconds: elapsed,
        paused: paused,
      };
      local.last_saved_at = isoNow();
      local.submitted = false;
      writeStored(quizId, local);
    }

    async function pushFullState() {
      ensureLocal();
      return postJson(stateUrl, {
        quiz_id: local.quiz_id,
        attempt_id: local.attempt_id,
        answers: local.answers,
        show_answers_in_sidebar: local.show_answers_in_sidebar,
        timer: local.timer,
        attempt_started_at: local.attempt_started_at,
        last_saved_at: local.last_saved_at,
      });
    }

    // POSTs that hit a 409 (server lost/replaced the attempt) resync the
    // full local state first, then retry once.
    async function apiPost(url, payload) {
      let res = await postJson(url, payload);
      if (res.status === 409) {
        await pushFullState();
        res = await postJson(url, payload);
      }
      return res;
    }

    // ── answers: extract / apply ───────────────────────────────────────

    const questionCards = Array.from(document.querySelectorAll(".bs-question-card"));

    function cardIndex(card) {
      const m = (card.id || "").match(/^q-(\d+)$/);
      return m ? parseInt(m[1], 10) : null;
    }

    function extractAnswer(card) {
      const multi = card.querySelectorAll('input[type="checkbox"][name^="answer_multi_"]');
      if (multi.length) {
        const letters = [];
        for (const el of multi) {
          if (el.checked) letters.push(el.value);
        }
        return letters.join(",");
      }

      const radio = card.querySelector('input[type="radio"][name^="answer_"]:checked');
      if (radio) return radio.value;

      const textarea = card.querySelector('textarea[name^="answer_"]');
      if (textarea) return (textarea.value || "").trim();

      const input = card.querySelector(
        'input[name^="answer_"]:not([type="radio"]):not([type="checkbox"])'
      );
      if (input) return (input.value || "").trim();

      const selects = card.querySelectorAll('select[name^="answer_match_"]');
      if (selects.length) {
        const pairs = [];
        for (const selectEl of selects) {
          const value = (selectEl.value || "").trim();
          if (!value) continue;
          const nameMatch = selectEl.name.match(/^answer_match_\d+_(.+)$/);
          if (!nameMatch) continue;
          pairs.push(nameMatch[1] + "-" + value);
        }
        return pairs.join(",");
      }

      return "";
    }

    function applyAnswerToCard(card, answer) {
      const boxes = card.querySelectorAll('input[type="checkbox"][name^="answer_multi_"]');
      if (boxes.length) {
        const chosen = new Set(
          String(answer || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        );
        for (const b of boxes) b.checked = chosen.has(b.value);
        return;
      }

      const radios = Array.from(card.querySelectorAll('input[type="radio"][name^="answer_"]'));
      if (radios.length) {
        const target = String(answer || "").trim().toUpperCase();
        for (const r of radios) r.checked = r.value.toUpperCase() === target;
        return;
      }

      const textarea = card.querySelector('textarea[name^="answer_"]');
      if (textarea) {
        textarea.value = answer || "";
        return;
      }

      const selects = card.querySelectorAll('select[name^="answer_match_"]');
      if (selects.length) {
        const pairs = {};
        for (const p of String(answer || "").split(",")) {
          const m = p.match(/^\s*([A-Za-z0-9]+)\s*-\s*([A-Za-z0-9]+)\s*$/);
          if (m) pairs[m[1]] = m[2];
        }
        for (const s of selects) {
          const nameMatch = s.name.match(/^answer_match_\d+_(.+)$/);
          if (nameMatch) s.value = pairs[nameMatch[1]] || "";
        }
      }
    }

    function applyAnswers(answers) {
      if (!answers) return;
      for (const card of questionCards) {
        const idx = cardIndex(card);
        if (idx === null) continue;
        const key = String(idx);
        if (Object.prototype.hasOwnProperty.call(answers, key)) {
          applyAnswerToCard(card, answers[key]);
        }
      }
    }

    function seedAnswersFromDom() {
      ensureLocal();
      for (const card of questionCards) {
        const idx = cardIndex(card);
        if (idx !== null) local.answers[String(idx)] = extractAnswer(card);
      }
    }

    // ── hydration on load ──────────────────────────────────────────────

    const attemptId = shell.dataset.attemptId || "";
    const serverSavedAt = shell.dataset.serverSavedAt || "";

    if (
      local &&
      local.attempt_id === attemptId &&
      timeNewer(local.last_saved_at, serverSavedAt)
    ) {
      // Local storage is ahead of the server (a save POST failed earlier):
      // re-apply to the DOM and resync the server.
      applyAnswers(local.answers);
      if (local.timer && typeof local.timer === "object") {
        const t = local.timer;
        const e = Math.floor(Number(t.elapsed_seconds));
        if (Number.isFinite(e) && e >= 0) elapsed = e;
        paused = !!t.paused;
        if (t.mode === "countdown") {
          const lim = Math.floor(Number(t.limit_seconds));
          if (Number.isFinite(lim) && lim > 0) limitSeconds = lim;
        }
      }
      if (typeof local.show_answers_in_sidebar === "boolean" && local.show_answers_in_sidebar !== showAnswers) {
        showAnswers = local.show_answers_in_sidebar;
        shell.dataset.showAnswers = showAnswers ? "1" : "0";
        const checkbox = shell.querySelector("#settingsShowAnswers");
        if (checkbox) checkbox.checked = showAnswers;
      }
      pushFullState();
      for (const card of questionCards) {
        void updateSidebarForCard(card);
      }
    } else if (!local || local.attempt_id !== attemptId) {
      // Fresh attempt started on the server — any stored entry is stale.
      local = null;
      ensureLocal();
      seedAnswersFromDom();
      persistLocal();
    }

    // ── sidebar tiles ──────────────────────────────────────────────────

    const gradeUrl = shell.dataset.gradeUrl || "";

    function isQuestionAnswered(cardEl) {
      const fields = cardEl.querySelectorAll("input, textarea, select");
      for (const el of fields) {
        if (el.tagName === "TEXTAREA") {
          if ((el.value || "").trim().length > 0) return true;
          continue;
        }
        if (el.tagName === "SELECT") {
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

    function clearStatusClasses(tile) {
      tile.classList.remove("is-correct", "is-partial", "is-incorrect");
    }

    async function requestGrade(idx, answer) {
      if (!gradeUrl) return null;
      const res = await fetch(gradeUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index: idx, answer: answer }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.status || null;
    }

    const gradeTimers = new Map();

    async function updateSidebarForCard(cardEl) {
      const idx = cardIndex(cardEl);
      if (idx === null) return;
      const tile = document.querySelector('.bs-nav-tile[data-question-index="' + idx + '"]');
      if (!tile) return;

      const answered = isQuestionAnswered(cardEl);
      tile.classList.toggle("is-answered", answered);

      const markEl = tile.querySelector(".bs-nav-mark");
      if (markEl) markEl.textContent = answered ? "✓" : "--";

      if (!showAnswers) {
        clearStatusClasses(tile);
        return;
      }

      const answer = extractAnswer(cardEl);
      if (!answer) {
        clearStatusClasses(tile);
        return;
      }

      const existing = gradeTimers.get(idx);
      if (existing) clearTimeout(existing);
      gradeTimers.set(
        idx,
        setTimeout(async () => {
          const status = await requestGrade(idx, answer);
          clearStatusClasses(tile);
          if (status) tile.classList.add("is-" + status);
        }, 200)
      );
    }

    // ── autosave ───────────────────────────────────────────────────────

    const saveTimers = new Map();

    function updateAnsweredCount() {
      ensureLocal();
      const answered = Object.values(local.answers).filter(
        (v) => typeof v === "string" && v.trim().length > 0
      ).length;
      const total = questionCards.length;
      const navProgress = document.getElementById("navProgress");
      const submitStatus = document.getElementById("submitStatus");
      if (navProgress) navProgress.textContent = answered + " of " + total + " saved";
      if (submitStatus) submitStatus.textContent = answered + " of " + total + " saved";
    }

    function queueSave(card) {
      const idx = cardIndex(card);
      if (idx === null) return;
      const existing = saveTimers.get(idx);
      if (existing) clearTimeout(existing);
      saveTimers.set(
        idx,
        setTimeout(async () => {
          ensureLocal();
          const answer = extractAnswer(card);
          local.answers[String(idx)] = answer;
          persistLocal();
          updateAnsweredCount();
          try {
            await apiPost(answerUrl, {
              index: idx,
              answer: answer,
              timer: {
                mode: isCountdown ? "countdown" : "stopwatch",
                limit_seconds: limitSeconds,
                elapsed_seconds: elapsed,
                paused: paused,
              },
            });
          } catch (e) {
            /* offline: local copy already saved; next load resyncs */
          }
        }, 350)
      );
    }

    for (const card of questionCards) {
      const handler = () => {
        void updateSidebarForCard(card);
        queueSave(card);
      };
      card.addEventListener("change", handler);
      card.addEventListener("input", handler);
    }

    // ── timer ticking ───────────────────────────────────────────────────

    function updateHiddenTimerFields() {
      const elapsedField = shell.querySelector('input[name="timer_elapsed_seconds"]');
      const pausedField = shell.querySelector('input[name="timer_paused"]');
      if (elapsedField) elapsedField.value = String(elapsed);
      if (pausedField) pausedField.value = paused ? "1" : "0";
    }

    let autoSubmitted = false;

    function autoSubmit() {
      if (autoSubmitted) return;
      autoSubmitted = true;
      const form = shell.querySelector(".bs-quiz-form");
      if (!form) return;
      const submitMarker = document.createElement("input");
      submitMarker.type = "hidden";
      submitMarker.name = "submit";
      submitMarker.value = "1";
      form.appendChild(submitMarker);
      updateHiddenTimerFields();
      form.requestSubmit();
    }

    window.setInterval(() => {
      if (paused || autoSubmitted) return;
      elapsed += 1;
      renderTimer();
      updateHiddenTimerFields();
      persistLocal();
      if (isCountdown && limitSeconds !== null && elapsed >= limitSeconds) {
        autoSubmit();
      }
    }, 1000);

    async function timerAction(action, minutes) {
      if (action === "pause") {
        paused = true;
      } else if (action === "resume") {
        paused = false;
      } else if (action === "add" && isCountdown && limitSeconds !== null) {
        limitSeconds += minutes * 60;
      }
      renderTimer();
      persistLocal();
      try {
        const res = await apiPost(timerUrl, { action: action, minutes: minutes });
        if (res && res.ok && res.data && typeof res.data === "object") {
          if (typeof res.data.paused === "boolean") paused = res.data.paused;
          const lim = Math.floor(Number(res.data.limit_seconds));
          if (isCountdown && Number.isFinite(lim) && lim > 0) limitSeconds = lim;
          renderTimer();
          persistLocal();
        }
      } catch (e) {
        /* offline: local state already updated */
      }
    }

    // Hover-only pause control next to the timer (tap reveals it on touch).
    if (timerToggleBtn) {
      timerToggleBtn.addEventListener("click", () => {
        void timerAction(paused ? "resume" : "pause");
      });
    }
    if (timerWrap) {
      timerWrap.addEventListener("click", (e) => {
        if (e.target === timerToggleBtn || timerToggleBtn.contains(e.target)) return;
        timerWrap.classList.toggle("is-revealed");
      });
    }

    // ── settings dropdown ──────────────────────────────────────────────

    const settingsBtn = shell.querySelector(".bs-settings-btn");
    const settingsMenu = shell.querySelector(".bs-settings-menu");

    function closeSettings() {
      if (!settingsMenu) return;
      settingsMenu.hidden = true;
      if (settingsBtn) settingsBtn.setAttribute("aria-expanded", "false");
    }

    if (settingsBtn && settingsMenu) {
      settingsBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        settingsMenu.hidden = !settingsMenu.hidden;
        settingsBtn.setAttribute("aria-expanded", settingsMenu.hidden ? "false" : "true");
      });

      document.addEventListener("click", (e) => {
        if (!settingsMenu.hidden && !settingsMenu.contains(e.target) && e.target !== settingsBtn) {
          closeSettings();
        }
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeSettings();
      });

      const showAnswersCheckbox = settingsMenu.querySelector("#settingsShowAnswers");
      if (showAnswersCheckbox) {
        showAnswersCheckbox.addEventListener("change", async () => {
          showAnswers = showAnswersCheckbox.checked;
          shell.dataset.showAnswers = showAnswers ? "1" : "0";
          ensureLocal();
          persistLocal();
          try {
            await apiPost(settingsUrl, { show_answers_in_sidebar: showAnswers });
          } catch (e) {
            /* offline: local copy already saved */
          }
          for (const card of questionCards) {
            void updateSidebarForCard(card);
          }
        });
      }

      settingsMenu.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-timer-action]");
        if (!btn) return;
        const action = btn.dataset.timerAction;
        const minutes = parseInt(btn.dataset.minutes || "0", 10);
        void timerAction(action, minutes);
      });
    }

    // ── exit confirmation ───────────────────────────────────────────────

    const exitModal = shell.querySelector("#exitModal");

    const exitTargets = shell.querySelectorAll("[data-exit]");
    for (const el of exitTargets) {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const target = el.getAttribute("href") || startUrl;
        if (!exitModal) {
          window.location.href = target;
          return;
        }
        exitModal.dataset.target = target;
        exitModal.hidden = false;
        const cancelBtn = exitModal.querySelector("#exitCancel");
        if (cancelBtn) cancelBtn.focus();
      });
    }

    if (exitModal) {
      exitModal.addEventListener("click", (e) => {
        if (e.target === exitModal) {
          exitModal.hidden = true;
        }
      });

      const cancelBtn = exitModal.querySelector("#exitCancel");
      if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
          exitModal.hidden = true;
        });
      }

      const confirmBtn = exitModal.querySelector("#exitConfirm");
      if (confirmBtn) {
        confirmBtn.addEventListener("click", () => {
          // Final local save so the attempt can be resumed later.
          if (!autoSubmitted) persistLocal();
          window.location.href = exitModal.dataset.target || startUrl;
        });
      }

      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !exitModal.hidden) {
          exitModal.hidden = true;
        }
      });
    }

    // ── submit ──────────────────────────────────────────────────────────

    const form = shell.querySelector(".bs-quiz-form");
    if (form) {
      form.addEventListener("submit", () => {
        autoSubmitted = true; // stop the tick loop during submit navigation
        for (const t of saveTimers.values()) clearTimeout(t);
        saveTimers.clear();
        ensureLocal();
        for (const card of questionCards) {
          const idx = cardIndex(card);
          if (idx !== null) local.answers[String(idx)] = extractAnswer(card);
        }
        local.submitted = true;
        writeStored(quizId, local);
        updateHiddenTimerFields();
      });
    }

    // Keep the stored timer fresh when leaving/switching tabs.
    window.addEventListener("pagehide", () => {
      if (!autoSubmitted) persistLocal();
    });

    renderTimer();
    updateHiddenTimerFields();
    updateAnsweredCount();
  }

  // ─────────────────────────────────────────────────────────────────────
  // Start page — resume banner
  // ─────────────────────────────────────────────────────────────────────

  function initStartPage() {
    const root = document.querySelector(".bs-start-card[data-quiz-id]");
    if (!root) return;

    const quizId = root.dataset.quizId || "";
    const stateUrl = root.dataset.stateUrl || "";
    const quizUrl = root.dataset.quizUrl || "/quiz";

    const local = readStored(quizId);
    if (!local || local.quiz_id !== quizId || local.submitted) return;

    const ago = document.getElementById("resumeAgo");
    const banner = document.getElementById("resumeBanner");
    const resumeBtn = document.getElementById("resumeBtn");
    const warning = document.getElementById("startWarning");
    const warningHint = document.getElementById("startWarningHint");

    if (ago) ago.textContent = relativeAgo(local.attempt_started_at);
    if (banner) banner.hidden = false;
    if (warning) warning.hidden = false;
    if (warningHint) warningHint.hidden = false;

    if (resumeBtn) {
      resumeBtn.addEventListener("click", async () => {
        resumeBtn.disabled = true;
        resumeBtn.textContent = "Resuming…";
        try {
          const res = await postJson(stateUrl, {
            quiz_id: local.quiz_id,
            attempt_id: local.attempt_id,
            answers: local.answers || {},
            show_answers_in_sidebar: !!local.show_answers_in_sidebar,
            timer: local.timer || {},
            attempt_started_at: local.attempt_started_at,
            last_saved_at: local.last_saved_at,
          });
          if (res.ok) {
            window.location.href = quizUrl;
            return;
          }
        } catch (e) {
          /* fall through */
        }
        resumeBtn.disabled = false;
        resumeBtn.textContent = "Resume attempt";
      });
    }
  }

  // ─────────────────────────────────────────────────────────────────────
  // Summary page — clear the stored attempt + format static timers
  // ─────────────────────────────────────────────────────────────────────

  function initSummaryPage() {
    const root = document.querySelector(".bs-summary-card[data-quiz-id]");
    if (root) {
      const local = readStored(root.dataset.quizId || "");
      if (local && local.attempt_id && local.attempt_id === root.dataset.attemptId) {
        clearStored(root.dataset.quizId || "");
      }
    }

    for (const el of document.querySelectorAll(".bs-timer[data-elapsed]")) {
      const base = parseInt(el.getAttribute("data-elapsed") || "0", 10);
      if (!Number.isNaN(base)) el.textContent = formatTime(base);
    }
  }

  // ─────────────────────────────────────────────────────────────────────
  // Boot
  // ─────────────────────────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    if (body.classList.contains("bs-page-quiz")) initQuizPage();
    else if (body.classList.contains("bs-page-start")) initStartPage();
    else if (body.classList.contains("bs-page-summary")) initSummaryPage();
  });
})();
