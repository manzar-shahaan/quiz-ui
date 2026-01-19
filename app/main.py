from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

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


@dataclass
class AttemptState:
    answers: Dict[int, str]  # question_index -> answer string
    show_answers_in_sidebar: bool = False
    submitted: bool = False
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    feedback_path: Optional[str] = None
    feedback_error: Optional[str] = None


_attempt_state = AttemptState(answers={})


def _get_quiz() -> Quiz:
    return current_app.config["QUIZ"]


@bp.route("/", methods=["GET"])
def start_page():
    quiz: Quiz = _get_quiz()
    return render_template("start.html", quiz=quiz, error=None, elapsed_seconds=None)


@bp.route("/start", methods=["POST"])
def start_quiz():
    global _attempt_state
    show_answers = bool(request.form.get("show_answers_in_sidebar"))

    _attempt_state = AttemptState(
        answers={},
        show_answers_in_sidebar=show_answers,
        submitted=False,
        started_at=datetime.now(),
        submitted_at=None,
        feedback_path=None,
        feedback_error=None,
    )
    return redirect(url_for("main.quiz_page", index=0), code=303)


@bp.route("/quiz", methods=["GET", "POST"])
def quiz_page():
    quiz: Quiz = _get_quiz()
    questions: List[Question] = quiz.questions
    total = len(questions)

    if total == 0:
        return render_template(
            "start.html",
            quiz=quiz,
            error="No questions were found in this practice_test.md.",
            elapsed_seconds=None,
        )

    try:
        index = int(request.args.get("index", "0"))
    except (TypeError, ValueError):
        index = 0
    index = max(0, min(index, total - 1))

    page_size = 5
    page_start = (index // page_size) * page_size
    page_end = min(total, page_start + page_size)
    page_questions = questions[page_start:page_end]

    # Map of existing answers/letters for quick lookup in template
    existing_answers: Dict[int, str] = {
        i: _attempt_state.answers.get(i, "") for i in range(total)
    }
    existing_letters_map: Dict[int, List[str]] = {
        i: re.findall(r"[A-Z]", ans.upper()) for i, ans in existing_answers.items()
    }

    if request.method == "POST":
        # Save answers for all questions on the current page
        for q in page_questions:
            if q.qtype == "multi":
                letters = request.form.getlist(f"answer_multi_{q.index}")
                ua = ",".join(letters)
            else:
                ua = request.form.get(f"answer_{q.index}", "").strip()
            if ua is not None:
                _attempt_state.answers[q.index] = ua

        if "next_page" in request.form:
            next_index = min(page_start + page_size, total - 1)
            return redirect(url_for("main.quiz_page", index=next_index))
        elif "prev_page" in request.form:
            prev_index = max(page_start - page_size, 0)
            return redirect(url_for("main.quiz_page", index=prev_index))
        elif "submit" in request.form:
            return redirect(url_for("main.summary_page"))

    current_answered = bool(existing_answers.get(index, "").strip())
    progress_pct = int((index + 1) / total * 100) if total else 0
    now = datetime.now()
    elapsed_seconds = 0
    if _attempt_state.started_at:
        elapsed_seconds = int((now - _attempt_state.started_at).total_seconds())

    def _answered(idx: int) -> bool:
        ans = _attempt_state.answers.get(idx)
        return bool(ans and str(ans).strip())

    answered_count = sum(1 for i in range(total) if _answered(i))

    show_answers_in_sidebar = _attempt_state.show_answers_in_sidebar

    def _status(idx: int) -> Optional[str]:
        if not show_answers_in_sidebar:
            return None
        ua = _attempt_state.answers.get(idx)
        if not ua or not str(ua).strip():
            return None
        score, _ = grading.grade_question(questions[idx], ua)
        if score >= 0.999:
            return "correct"
        if score > 0:
            return "partial"
        return "incorrect"

    nav_pages = []
    for start in range(0, total, page_size):
        page_num = start // page_size + 1
        page_items = []
        for i in range(start, min(start + page_size, total)):
            q = questions[i]
            page_items.append(
                {
                    "index": i,
                    "display": q.file_qnum,
                    "answered": _answered(i),
                    "current": i == index,
                    "status": _status(i),
                }
            )
        nav_pages.append({"page_num": page_num, "entries": page_items})

    page_index = index // page_size + 1 if total else 0
    total_pages = (total + page_size - 1) // page_size if total else 0

    return render_template(
        "quiz.html",
        quiz=quiz,
        index=index,
        total=total,
        elapsed_seconds=elapsed_seconds,
        nav_pages=nav_pages,
        page_index=page_index,
        total_pages=total_pages,
        answered_count=answered_count,
        current_answered=current_answered,
        page_questions=page_questions,
        page_start=page_start,
        page_end=page_end,
        existing_answers=existing_answers,
        existing_letters_map=existing_letters_map,
        show_answers_in_sidebar=show_answers_in_sidebar,
    )


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

    time_taken_seconds = 0

    if _attempt_state.submitted_at and not _attempt_state.started_at:
        _attempt_state.started_at = _attempt_state.submitted_at

    if _attempt_state.started_at and _attempt_state.submitted_at:
        time_taken_seconds = int((_attempt_state.submitted_at - _attempt_state.started_at).total_seconds())

    total_questions = len(results)
    total_points = sum(score for _, _, score, _ in results)
    pct = (total_points / total_questions * 100) if total_questions else 0.0

    return render_template(
        "summary.html",
        quiz=quiz,
        results=results,
        total_questions=total_questions,
        total_points=total_points,
        pct=pct,
        feedback_path=_attempt_state.feedback_path,
        feedback_error=_attempt_state.feedback_error,
        time_taken_seconds=time_taken_seconds,
        elapsed_seconds=None,
    )
