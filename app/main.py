from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .models import Quiz, Question
from . import grading, feedback

bp = Blueprint("main", __name__)

TIMER_ADD_MINUTES = (5, 15)


@dataclass
class AttemptState:
    """All mutable state for the current (single-user) attempt.

    Elapsed time is accumulated by the browser while the quiz page is open
    (pausing freezes it) and synced to the server on every autosave.
    Wall-clock ``started_at`` is only kept for the "started X ago" resume notice.
    """

    active: bool = False
    attempt_id: str = ""
    answers: Dict[int, str] = field(default_factory=dict)
    show_answers_in_sidebar: bool = False
    timer_mode: str = "stopwatch"  # "stopwatch" | "countdown"
    timer_limit_seconds: Optional[int] = None
    timer_elapsed_seconds: int = 0
    timer_paused: bool = False
    started_at: Optional[datetime] = None
    last_saved_at: Optional[datetime] = None
    submitted: bool = False
    timed_out: bool = False
    submitted_at: Optional[datetime] = None
    feedback_path: Optional[str] = None
    feedback_error: Optional[str] = None

    def in_progress(self) -> bool:
        return self.active and not self.submitted


_attempt_state = AttemptState()


def _get_quiz() -> Quiz:
    return current_app.config["QUIZ"]


def _get_quiz_id() -> str:
    return current_app.config.get("QUIZ_ID", "")


def _remaining_seconds(state: AttemptState) -> Optional[int]:
    if state.timer_mode != "countdown" or state.timer_limit_seconds is None:
        return None
    return max(0, state.timer_limit_seconds - state.timer_elapsed_seconds)


def _is_time_up(state: AttemptState) -> bool:
    remaining = _remaining_seconds(state)
    return remaining is not None and remaining <= 0


def _parse_iso(value) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _apply_timer_payload(payload) -> None:
    """Adopt a timer snapshot pushed by the client (elapsed/paused only)."""
    if not isinstance(payload, dict):
        return
    elapsed = payload.get("elapsed_seconds")
    if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and elapsed >= 0:
        _attempt_state.timer_elapsed_seconds = int(elapsed)
    if "paused" in payload:
        _attempt_state.timer_paused = bool(payload["paused"])


@bp.route("/", methods=["GET"])
def start_page():
    quiz: Quiz = _get_quiz()
    return render_template(
        "start.html",
        quiz=quiz,
        quiz_id=_get_quiz_id(),
        error=None,
        timer_minutes="",
        show_answers_in_sidebar=False,
        page_variant="start",
    )


@bp.route("/start", methods=["POST"])
def start_quiz():
    global _attempt_state
    show_answers = bool(request.form.get("show_answers_in_sidebar"))
    timer_minutes_raw = (request.form.get("timer_minutes") or "").strip()
    time_limit_seconds: Optional[int] = None

    if timer_minutes_raw:
        try:
            timer_minutes = int(timer_minutes_raw)
        except ValueError:
            quiz: Quiz = _get_quiz()
            return render_template(
                "start.html",
                quiz=quiz,
                quiz_id=_get_quiz_id(),
                error="Timer must be a whole number of minutes.",
                timer_minutes=timer_minutes_raw,
                show_answers_in_sidebar=show_answers,
                page_variant="start",
            )

        if timer_minutes <= 0:
            quiz = _get_quiz()
            return render_template(
                "start.html",
                quiz=quiz,
                quiz_id=_get_quiz_id(),
                error="Timer must be greater than 0 minutes.",
                timer_minutes=timer_minutes_raw,
                show_answers_in_sidebar=show_answers,
                page_variant="start",
            )

        time_limit_seconds = timer_minutes * 60

    now = datetime.now()
    _attempt_state = AttemptState(
        active=True,
        attempt_id=uuid.uuid4().hex,
        answers={},
        show_answers_in_sidebar=show_answers,
        timer_mode="countdown" if time_limit_seconds else "stopwatch",
        timer_limit_seconds=time_limit_seconds,
        timer_elapsed_seconds=0,
        timer_paused=False,
        started_at=now,
        last_saved_at=now,
    )
    return redirect(url_for("main.quiz_page"), code=303)


@bp.route("/quiz", methods=["GET", "POST"])
def quiz_page():
    quiz: Quiz = _get_quiz()
    questions: List[Question] = quiz.questions
    total = len(questions)

    if total == 0:
        return render_template(
            "start.html",
            quiz=quiz,
            quiz_id=_get_quiz_id(),
            error="No questions were found in this practice_test.md.",
            timer_minutes="",
            show_answers_in_sidebar=False,
            page_variant="start",
        )

    state = _attempt_state

    if request.method == "POST":
        # Single-page submit: the form contains every question.
        if not state.in_progress():
            return redirect(url_for("main.start_page"))

        for q in questions:
            if q.qtype == "multi":
                letters = request.form.getlist(f"answer_multi_{q.index}")
                ua = ",".join(letters)
            elif q.qtype == "match":
                pairs: list[str] = []
                for left in q.match_left or []:
                    val = request.form.get(f"answer_match_{q.index}_{left.label}", "").strip()
                    if val:
                        pairs.append(f"{left.label}-{val}")
                ua = ",".join(pairs)
            else:
                ua = request.form.get(f"answer_{q.index}", "").strip()
            state.answers[q.index] = ua

        # Final timer snapshot from the client (hidden fields, kept fresh by quiz.js).
        raw_elapsed = request.form.get("timer_elapsed_seconds", "")
        if raw_elapsed.isdigit():
            state.timer_elapsed_seconds = max(0, int(raw_elapsed))
        state.timer_paused = request.form.get("timer_paused") == "1"
        state.last_saved_at = datetime.now()

        if _is_time_up(state):
            state.timed_out = True

        return redirect(url_for("main.summary_page"))

    # GET
    if state.submitted:
        return redirect(url_for("main.summary_page"))

    if state.in_progress() and _is_time_up(state):
        state.timed_out = True
        return redirect(url_for("main.summary_page"))

    existing_answers: Dict[int, str] = {
        i: state.answers.get(i, "") for i in range(total)
    }
    existing_letters_map: Dict[int, List[str]] = {
        i: re.findall(r"[A-Z]", ans.upper()) for i, ans in existing_answers.items()
    }

    def _answered(idx: int) -> bool:
        ans = state.answers.get(idx)
        return bool(ans and str(ans).strip())

    answered_count = sum(1 for i in range(total) if _answered(i))

    show_answers_in_sidebar = state.show_answers_in_sidebar

    def _status(idx: int) -> Optional[str]:
        if not show_answers_in_sidebar:
            return None
        ua = state.answers.get(idx)
        if not ua or not str(ua).strip():
            return None
        score, _ = grading.grade_question(questions[idx], ua)
        if score >= 0.999:
            return "correct"
        if score > 0:
            return "partial"
        return "incorrect"

    nav_items = [
        {
            "index": i,
            "display": q.file_qnum,
            "answered": _answered(i),
            "status": _status(i),
        }
        for i, q in enumerate(questions)
    ]

    return render_template(
        "quiz.html",
        quiz=quiz,
        quiz_id=_get_quiz_id(),
        attempt_id=state.attempt_id if state.in_progress() else "",
        has_attempt=state.in_progress(),
        server_saved_at=(
            state.last_saved_at.isoformat() if state.in_progress() and state.last_saved_at else ""
        ),
        started_at=(
            state.started_at.isoformat() if state.in_progress() and state.started_at else ""
        ),
        total=total,
        questions=questions,
        existing_answers=existing_answers,
        existing_letters_map=existing_letters_map,
        answered_count=answered_count,
        nav_items=nav_items,
        show_answers_in_sidebar=show_answers_in_sidebar,
        timer_mode=state.timer_mode,
        timer_limit_seconds=state.timer_limit_seconds,
        timer_elapsed_seconds=state.timer_elapsed_seconds,
        timer_paused=state.timer_paused,
        remaining_seconds=_remaining_seconds(state),
        page_variant="quiz",
    )


@bp.route("/api/attempt/answer", methods=["POST"])
def api_attempt_answer():
    """Autosave a single question's answer plus a timer snapshot."""
    if not _attempt_state.in_progress():
        return jsonify({"error": "no_attempt"}), 409

    data = request.get_json(silent=True) or {}
    idx_raw = data.get("index")
    if idx_raw is None:
        return jsonify({"error": "bad_index"}), 400

    try:
        idx = int(idx_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "bad_index"}), 400

    quiz = _get_quiz()
    if idx < 0 or idx >= len(quiz.questions):
        return jsonify({"error": "out_of_range"}), 400

    _attempt_state.answers[idx] = str(data.get("answer") or "")
    _apply_timer_payload(data.get("timer"))
    _attempt_state.last_saved_at = datetime.now()
    return jsonify({"ok": True})


@bp.route("/api/attempt/state", methods=["POST"])
def api_attempt_state():
    """Restore/sync the full attempt (pushed from localStorage by the client)."""
    global _attempt_state

    data = request.get_json(silent=True) or {}
    if data.get("quiz_id") != _get_quiz_id():
        return jsonify({"error": "quiz_mismatch"}), 400

    quiz = _get_quiz()
    total = len(quiz.questions)

    raw_answers = data.get("answers")
    answers: Dict[int, str] = {}
    if isinstance(raw_answers, dict):
        for k, v in raw_answers.items():
            try:
                idx = int(k)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < total:
                answers[idx] = str(v or "")

    raw_timer = data.get("timer")
    timer = raw_timer if isinstance(raw_timer, dict) else {}
    raw_mode = str(timer.get("mode") or "")
    mode = raw_mode if raw_mode in ("stopwatch", "countdown") else "stopwatch"
    limit = timer.get("limit_seconds")
    if mode == "countdown":
        if not isinstance(limit, (int, float)) or isinstance(limit, bool) or limit <= 0:
            return jsonify({"error": "bad_timer"}), 400
        limit_seconds: Optional[int] = int(limit)
    else:
        limit_seconds = None

    elapsed = timer.get("elapsed_seconds")
    elapsed_seconds = int(elapsed) if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and elapsed >= 0 else 0

    now = datetime.now()
    attempt_id = str(data.get("attempt_id") or uuid.uuid4().hex)

    _attempt_state = AttemptState(
        active=True,
        attempt_id=attempt_id,
        answers=answers,
        show_answers_in_sidebar=bool(data.get("show_answers_in_sidebar")),
        timer_mode=mode,
        timer_limit_seconds=limit_seconds,
        timer_elapsed_seconds=elapsed_seconds,
        timer_paused=bool(timer.get("paused")),
        started_at=_parse_iso(data.get("attempt_started_at")) or now,
        last_saved_at=now,
    )
    return jsonify({"ok": True, "attempt_id": attempt_id})


@bp.route("/api/attempt/timer", methods=["POST"])
def api_attempt_timer():
    if not _attempt_state.in_progress():
        return jsonify({"error": "no_attempt"}), 409

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("pause", "resume", "add"):
        return jsonify({"error": "bad_action"}), 400

    if action == "add":
        minutes = data.get("minutes")
        if minutes not in TIMER_ADD_MINUTES:
            return jsonify({"error": "bad_minutes"}), 400
        if _attempt_state.timer_mode != "countdown" or _attempt_state.timer_limit_seconds is None:
            return jsonify({"error": "not_countdown"}), 400
        _attempt_state.timer_limit_seconds += int(minutes) * 60
    elif action == "pause":
        _attempt_state.timer_paused = True
    else:
        _attempt_state.timer_paused = False

    _attempt_state.last_saved_at = datetime.now()
    return jsonify(
        {
            "ok": True,
            "paused": _attempt_state.timer_paused,
            "limit_seconds": _attempt_state.timer_limit_seconds,
            "elapsed_seconds": _attempt_state.timer_elapsed_seconds,
        }
    )


@bp.route("/api/attempt/settings", methods=["POST"])
def api_attempt_settings():
    if not _attempt_state.in_progress():
        return jsonify({"error": "no_attempt"}), 409

    data = request.get_json(silent=True) or {}
    _attempt_state.show_answers_in_sidebar = bool(data.get("show_answers_in_sidebar"))
    _attempt_state.last_saved_at = datetime.now()
    return jsonify({"ok": True, "show_answers_in_sidebar": _attempt_state.show_answers_in_sidebar})


@bp.route("/api/grade", methods=["POST"])
def grade_api():
    if not _attempt_state.show_answers_in_sidebar:
        return jsonify({"error": "not_enabled"}), 403

    data = request.get_json(silent=True) or {}

    idx_raw = data.get("index")
    if idx_raw is None:
        return jsonify({"error": "bad_index"}), 400

    try:
        idx = int(idx_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "bad_index"}), 400

    answer = str(data.get("answer") or "").strip()
    quiz = _get_quiz()

    if idx < 0 or idx >= len(quiz.questions):
        return jsonify({"error": "out_of_range"}), 400

    if not answer:
        return jsonify({"status": None})

    score, _ = grading.grade_question(quiz.questions[idx], answer)
    if score >= 0.999:
        status = "correct"
    elif score > 0:
        status = "partial"
    else:
        status = "incorrect"

    return jsonify({"status": status})


def _build_result_detail(q: Question, ua: Optional[str], score: float, correct_disp: str) -> dict:
    ua = ua or ""
    status = "correct" if score >= 0.999 else ("partial" if score > 0 else "incorrect")
    detail: dict = {"q": q, "ua": ua, "score": score, "correct_disp": correct_disp, "status": status}

    if q.qtype in ("mc", "multi"):
        correct_letters = set(re.findall(r"[A-Z]", correct_disp.upper()))
        user_letters = set(re.findall(r"[A-Z]", ua.upper())) if ua else set()
        option_states = []
        for opt in (q.options or []):
            is_correct = opt.label in correct_letters
            is_chosen = opt.label in user_letters
            if is_correct and is_chosen:
                state = "correct-chosen"
            elif is_correct:
                state = "correct-missed"
            elif is_chosen:
                state = "wrong-chosen"
            else:
                state = "neutral"
            option_states.append({"opt": opt, "state": state})
        detail["option_states"] = option_states

    elif q.qtype == "t/f":
        correct_t = correct_disp.strip().lower() == "true"
        if ua:
            user_t: Optional[bool] = ua.strip().lower() in ("t", "true")
        else:
            user_t = None
        tf_states = []
        for is_true_opt, label in [(True, "True"), (False, "False")]:
            is_correct = is_true_opt == correct_t
            is_chosen = user_t is not None and is_true_opt == user_t
            if is_correct and is_chosen:
                state = "correct-chosen"
            elif is_correct:
                state = "correct-missed"
            elif is_chosen:
                state = "wrong-chosen"
            else:
                state = "neutral"
            tf_states.append({"label": label, "state": state})
        detail["tf_states"] = tf_states

    elif q.qtype == "match":
        correct_map = q.match_map or {}
        pairs = re.findall(r"(\d+)\s*-\s*([A-Z])", ua.upper()) if ua else []
        user_map = {num: letter for num, letter in pairs}
        opts_by_label = {opt.label: opt.text for opt in (q.options or [])}
        match_rows = []
        for left in (q.match_left or []):
            correct_r = correct_map.get(left.label, "?")
            user_r = user_map.get(left.label)
            is_correct_match = user_r == correct_r if user_r else False
            match_rows.append({
                "left": left,
                "correct_r": correct_r,
                "correct_text": opts_by_label.get(correct_r, correct_r),
                "user_r": user_r or "—",
                "user_text": opts_by_label.get(user_r, user_r) if user_r else "—",
                "is_correct": is_correct_match,
            })
        detail["match_rows"] = match_rows

    return detail


@bp.route("/summary", methods=["GET"])
def summary_page():
    quiz: Quiz = _get_quiz()
    questions: List[Question] = quiz.questions

    results: List[Tuple[Question, Optional[str], float, str]] = []

    for q in questions:
        ua = _attempt_state.answers.get(q.index)
        if ua is None:
            results.append((q, None, 0.0, ""))  # unanswered
        else:
            score, correct_disp = grading.grade_question(q, ua)
            results.append((q, ua, score, correct_disp))

    if not _attempt_state.submitted:
        _attempt_state.submitted_at = datetime.now()
        _attempt_state.timed_out = _is_time_up(_attempt_state)

        # Generate a feedback file beside the practice test (only once).
        try:
            practice_path = Path(current_app.config["QUIZ_PATH"])
            out_path = feedback.write_feedback_md(practice_path=practice_path, results=results)
            _attempt_state.feedback_path = str(out_path)
            _attempt_state.feedback_error = None
        except Exception as e:  # pragma: no cover
            _attempt_state.feedback_path = None
            _attempt_state.feedback_error = str(e)

        _attempt_state.submitted = True

    time_taken_seconds = _attempt_state.timer_elapsed_seconds

    total_questions = len(results)
    total_points = sum(score for _, _, score, _ in results)
    pct = (total_points / total_questions * 100) if total_questions else 0.0

    result_details = [_build_result_detail(q, ua, score, correct_disp) for q, ua, score, correct_disp in results]

    return render_template(
        "summary.html",
        quiz=quiz,
        quiz_id=_get_quiz_id(),
        attempt_id=_attempt_state.attempt_id,
        result_details=result_details,
        total_questions=total_questions,
        total_points=total_points,
        pct=pct,
        feedback_path=_attempt_state.feedback_path,
        feedback_error=_attempt_state.feedback_error,
        time_taken_seconds=time_taken_seconds,
        timed_out=_attempt_state.timed_out,
        page_variant="summary",
    )
