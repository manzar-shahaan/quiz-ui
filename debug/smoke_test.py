"""Smoke test: exercise every route of the redesigned quiz flow.

Run:  .venv/bin/python debug/smoke_test.py
"""
from pathlib import Path

from app import create_app

HERE = Path(__file__).resolve().parent
QUIZ = HERE / "smoke_quiz.md"

app = create_app(QUIZ)
c = app.test_client()

failures = []


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  ({extra})" if extra and not cond else ""))
    if not cond:
        failures.append(name)


# ── start page ──────────────────────────────────────────────────────────
r = c.get("/")
check("GET / -> 200", r.status_code == 200)
body = r.get_data(as_text=True)
check("start page has resume banner markup", 'id="resumeBanner"' in body)
check("start page has data-quiz-id", "data-quiz-id" in body)

# ── quiz without attempt → renders inert page (JS redirects/restores) ──
r = c.get("/quiz")
check("GET /quiz (no attempt) -> 200 inert", r.status_code == 200)
body = r.get_data(as_text=True)
check("no attempt flagged", 'data-has-attempt="0"' in body)

# ── start a timed attempt ───────────────────────────────────────────────
r = c.post("/start", data={"timer_minutes": "10", "show_answers_in_sidebar": "1"})
check("POST /start -> 303", r.status_code == 303)

r = c.get("/quiz")
body = r.get_data(as_text=True)
check("GET /quiz (attempt) -> 200", r.status_code == 200)
check("has attempt flagged", 'data-has-attempt="1"' in body)
check("countdown mode", 'data-limit-seconds="600"' in body)
check("all 10 questions rendered", body.count('class="bs-question-card"') == 10)
check("single-page form contains submit button", 'name="submit"' in body)
check("settings dropdown present", 'bs-settings-btn' in body)
check("+5/+15 buttons present", body.count("data-minutes=") == 2)
check("exit modal present", 'id="exitModal"' in body)
check("sidebar has 10 tiles", body.count("bs-nav-tile ") + body.count('bs-nav-tile"') == 10)

# ── autosave endpoints ─────────────────────────────────────────────────
r = c.post("/api/attempt/answer", json={"index": 0, "answer": "B", "timer": {"elapsed_seconds": 5, "paused": False}})
check("autosave answer 0", r.status_code == 200 and r.get_json().get("ok") is True)

r = c.post("/api/attempt/answer", json={"index": 1, "answer": "B,D", "timer": {"elapsed_seconds": 6, "paused": False}})
check("autosave answer 1", r.status_code == 200)

r = c.get("/quiz")
body = r.get_data(as_text=True)
check("answer reflected on reload (B,D checked)", 'answer_multi_1" value="B" checked' in body.replace("\n", " ").replace("  ", " ") or "value=\"B\"\n                    checked" in body)
check("elapsed seconds from client adopted", 'data-elapsed-seconds="6"' in body)

# invalid index
r = c.post("/api/attempt/answer", json={"index": 99, "answer": "B"})
check("autosave bad index -> 400", r.status_code == 400)

# ── timer controls ──────────────────────────────────────────────────────
r = c.post("/api/attempt/timer", json={"action": "pause"})
check("timer pause", r.status_code == 200 and r.get_json()["paused"] is True)

r = c.post("/api/attempt/timer", json={"action": "add", "minutes": 5})
check("timer add 5min", r.status_code == 200 and r.get_json()["limit_seconds"] == 900)

r = c.post("/api/attempt/timer", json={"action": "add", "minutes": 7})
check("timer add 7min rejected", r.status_code == 400)

r = c.post("/api/attempt/timer", json={"action": "resume"})
check("timer resume", r.status_code == 200 and r.get_json()["paused"] is False)

# ── settings toggle ─────────────────────────────────────────────────────
r = c.post("/api/attempt/settings", json={"show_answers_in_sidebar": False})
check("settings toggle off", r.status_code == 200)

r = c.post("/api/grade", json={"index": 0, "answer": "B"})
check("grade api gated when disabled", r.status_code == 403)

r = c.post("/api/attempt/settings", json={"show_answers_in_sidebar": True})
r = c.post("/api/grade", json={"index": 0, "answer": "B"})
check("grade api works when enabled", r.status_code == 200 and r.get_json()["status"] == "correct")

# ── restore (server restart simulation) ─────────────────────────────────
r = c.post(
    "/api/attempt/state",
    json={
        "quiz_id": app.config["QUIZ_ID"],
        "attempt_id": "test-restore-id",
        "answers": {"0": "A", "2": "T", "3": "1-A,2-B"},
        "show_answers_in_sidebar": False,
        "timer": {"mode": "countdown", "limit_seconds": 120, "elapsed_seconds": 30, "paused": True},
        "attempt_started_at": "2026-10-20T09:00:00",
    },
)
check("restore state", r.status_code == 200 and r.get_json()["attempt_id"] == "test-restore-id")

r = c.get("/quiz")
body = r.get_data(as_text=True)
check("restored attempt active", 'data-attempt-id="test-restore-id"' in body)
check("restored timer state (120s limit, 30 elapsed, paused)", 'data-limit-seconds="120"' in body and 'data-elapsed-seconds="30"' in body and 'data-paused="1"' in body)

# quiz_id mismatch rejected
r = c.post("/api/attempt/state", json={"quiz_id": "wrong", "answers": {}})
check("restore wrong quiz rejected", r.status_code == 400)

# ── time-up auto submit path (server side) ──────────────────────────────
c.post("/api/attempt/timer", json={"action": "resume"})
c.post("/api/attempt/answer", json={"index": 0, "answer": "B", "timer": {"elapsed_seconds": 130, "paused": False}})
r = c.get("/quiz")
check("time-up redirects to summary", r.status_code == 302 and "/summary" in r.headers["Location"])

r = c.get("/summary")
check("summary renders after timeout", r.status_code == 200)
body = r.get_data(as_text=True)
check("summary notes timeout", "automatically" in body)

# ── stopwatch flow + no-JS form submit ──────────────────────────────────
c2app = create_app(QUIZ)
c2 = c2app.test_client()
c2.post("/start", data={})  # blank timer → stopwatch
r = c2.get("/quiz")
body = r.get_data(as_text=True)
check("stopwatch mode (no limit attr content)", 'data-limit-seconds=""' in body)

# simulate the classic form POST with all answers
r = c2.post(
    "/quiz",
    data={
        "answer_0": "B",
        "answer_multi_1": ["B", "D"],
        "answer_2": "T",
        "answer_match_3_1": "A",
        "answer_match_3_2": "B",
        "answer_4": "B",
        "answer_5": "A",   # wrong
        "timer_elapsed_seconds": "42",
        "timer_paused": "0",
        "submit": "1",
    },
)
check("form submit redirects to summary", r.status_code == 302 and "/summary" in r.headers["Location"])

r = c2.get("/summary")
body = r.get_data(as_text=True)
check("summary shows score", "Score:" in body)
check("summary uses timer elapsed", 'data-elapsed="42"' in body)

# submitted attempt: /quiz now redirects to summary
r = c2.get("/quiz")
check("quiz after submit redirects to summary", r.status_code == 302 and "/summary" in r.headers["Location"])

# ── format checker (CLI --check) ────────────────────────────────────────
from app.checker import check_quiz_file, validate_quiz_text

issues, count = check_quiz_file(QUIZ)
check("checker: smoke quiz passes", not issues and count == 10)

bad = HERE / "bad_quiz.md"
bad_issues, bad_count = check_quiz_file(bad)
joined = " | ".join(bad_issues)
check("checker: bad quiz has issues", len(bad_issues) == 10 and bad_count == 6)
check("checker: catches answer not among options", "does not match any option" in joined)
check("checker: catches out-of-sequence options", "out of sequence" in joined)
check("checker: catches repeated multi letters", "repeats a letter" in joined and "Multi answer letters" in joined)
check("checker: catches bad T/F answer", "T/F answer must be T or F" in joined)
check("checker: catches match out-of-range/missing", "Match answer numbers" in joined and "does not cover left items" in joined)
check("checker: catches unknown type tag", "unknown type tag" in joined)
check("checker: catches missing Answer line", "no 'Answer:' line" in joined)
check("checker: catches missing title", "missing quiz title" in joined)

issues3, _ = validate_quiz_text("# T\n\n1) (MC) no answer\n   A) x\n   B) y\n")
check("checker: missing answer in otherwise-valid file", any("no 'Answer:' line" in s for s in issues3))

# ── result ─────────────────────────────────────────────────────────────-
print()
if failures:
    print(f"{len(failures)} FAILURES:")
    for f in failures:
        print(" -", f)
    raise SystemExit(1)
print("All checks passed.")
