from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .models import Question


def extract_test_number(practice_path: Path) -> int:
    """Extract first integer from filename stem; returns 0 if none."""
    match = re.search(r"(\d+)", practice_path.stem)
    return int(match.group(1)) if match else 0


def write_feedback_md(
    practice_path: Path,
    results: List[Tuple[Question, Optional[str], float, str]],
) -> Path:
    """Write a feedback markdown file next to the practice test.

    Output filename: `test {x} feedback {YYYY-MM-DD HH-MM-SS}.md`
    """

    now = dt.datetime.now()
    x = extract_test_number(practice_path)

    timestamp_for_name = now.strftime("%Y-%m-%d %H-%M-%S")
    out_name = f"test {x} feedback {timestamp_for_name}.md"
    out_path = practice_path.parent / out_name

    attempted = [(q, ua, score, correct) for (q, ua, score, correct) in results if ua is not None]
    total_attempted = len(attempted)

    if total_attempted == 0:
        body = [
            f"# Test {x} Feedback",
            "",
            f"- Practice file: `{practice_path.name}`",
            f"- Date/time: {now.strftime('%Y-%m-%d %I:%M:%S %p')}",
            "",
            "No questions attempted.",
        ]
        out_path.write_text("\n".join(body) + "\n", encoding="utf-8")
        return out_path

    total_points = sum(score for _, _, score, _ in attempted)
    num_full_correct = sum(1 for _, _, score, _ in attempted if score >= 0.999)
    pct = total_points / total_attempted * 100

    weak = [
        (q, ua, correct, score)
        for (q, ua, score, correct) in attempted
        if ua is not None and score < 0.999
    ]

    lines: list[str] = []
    lines.append(f"# Test {x} Feedback")
    lines.append("")
    lines.append(f"- Practice file: `{practice_path.name}`")
    lines.append(f"- Date/time: {now.strftime('%Y-%m-%d %I:%M:%S %p')}")
    lines.append("")
    lines.append("## Score")
    lines.append("")
    lines.append(f"- Points: **{total_points:.2f}/{total_attempted}** (**{pct:.1f}%**)")
    lines.append(f"- Fully correct: **{num_full_correct}/{total_attempted}**")
    lines.append("")

    if weak:
        lines.append("## Questions to review (incorrect or partial)")
        lines.append("")
        for q, ua, correct, score in weak:
            if score <= 0:
                tag = "incorrect"
            else:
                tag = f"partial ({score * 100:.1f}%)"

            lines.append(f"### #{q.file_qnum}: {q.title}")
            lines.append("")
            lines.append(f"- Type: `{q.qtype}`")
            lines.append(f"- Your answer: `{ua}`")
            lines.append(f"- Correct answer: `{correct}`")
            lines.append(f"- Result: **{tag}**")
            lines.append("")
    else:
        lines.append("## Review")
        lines.append("")
        lines.append("No incorrect or partial answers on this attempt.")
        lines.append("")

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path
