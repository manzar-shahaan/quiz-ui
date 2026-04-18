from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from .models import Quiz, Question, QuestionType, Option


def parse_match_answer(ans: str) -> Dict[str, str]:
    pairs = re.findall(r"(\d+)\s*-\s*([A-Z])", ans.upper())
    return {num: letter for num, letter in pairs}


def parse_match_columns(prompt_lines: List[str]) -> tuple[list[Option], list[Option]]:
    left: list[Option] = []
    right: list[Option] = []

    for line in prompt_lines[1:]:
        l_num = re.match(r"^\s*(\d+)\)\s*(.*)$", line)
        r_letter = re.match(r"^\s*([A-Z])\)\s*(.*)$", line)
        if l_num:
            left.append(Option(label=l_num.group(1), text=l_num.group(2).rstrip()))
        elif r_letter:
            right.append(Option(label=r_letter.group(1), text=r_letter.group(2).rstrip()))
    return left, right


def parse_quiz(path: Path) -> Quiz:
    text = path.read_text(encoding="utf-8")

    lines = text.splitlines()

    # ----- Title -----
    title = "Quiz"
    i = 0
    while i < len(lines) and not lines[i].lstrip().startswith("#"):
        i += 1
    if i < len(lines):
        title = lines[i].lstrip("#").strip()
        i += 1

    # ----- Meta bullets -----
    meta_lines: list[str] = []
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("- "):
            meta_lines.append(stripped)
            i += 1
        elif stripped == "":
            i += 1
        else:
            break

    # ----- Questions -----
    questions: List[Question] = []
    n = len(lines)
    idx = 0

    while idx < n:
        line = lines[idx]

        # "1) (MC) ..." or "  1) ..."
        m = re.match(r"^\s*(\d+)\)\s*(.*)$", line)
        if not m:
            idx += 1
            continue

        file_qnum = int(m.group(1))
        rest = m.group(2).strip()

        type_match = re.search(r"\(([^)]+)\)", rest)
        if type_match:
            type_str = type_match.group(1).strip().lower()
            after_type = rest[type_match.end():].strip()
        else:
            type_str = ""
            after_type = rest

        if "match" in type_str:
            qtype: QuestionType = "match"
        elif "multi" in type_str:
            qtype = "multi"
        elif "t/f" in type_str or "true" in type_str or "false" in type_str:
            qtype = "t/f"
        else:
            qtype = "mc"

        title_line = after_type or "(no short title)"

        # Collect full block until Answer:
        prompt_lines = [line]
        idx += 1
        answer_line = None

        while idx < n:
            cur = lines[idx]
            if re.search(r"\banswer\s*:", cur, re.IGNORECASE):
                answer_line = cur
                idx += 1
                break
            prompt_lines.append(cur)
            idx += 1

        if not answer_line:
            continue

        ans_match = re.search(r"\banswer\s*:\s*(.*)$", answer_line, re.IGNORECASE)
        if not ans_match:
            continue
        ans_raw = ans_match.group(1).strip()

        # --- Parse options (multi-line) ---
        # Lines like "A) CREATE TABLE Child (" followed by indented continuation lines.
        options: List[Option] = []
        j = 1
        while j < len(prompt_lines):
            line_j = prompt_lines[j]
            opt_head = re.match(r"^\s*([A-Z])\)\s*(.*)$", line_j)
            if opt_head:
                label = opt_head.group(1)
                first_text = opt_head.group(2).rstrip()

                cont_lines: List[str] = []
                k = j + 1
                while k < len(prompt_lines):
                    next_line = prompt_lines[k]
                    # Stop if next option starts (B)...) or we accidentally hit Answer (paranoia)
                    if re.match(r"^\s*[A-Z]\)\s+", next_line):
                        break
                    if re.search(r"\banswer\s*:", next_line, re.IGNORECASE):
                        break
                    cont_lines.append(next_line.rstrip())
                    k += 1

                full_text = "\n".join([first_text] + cont_lines).rstrip()
                options.append(Option(label=label, text=full_text))
                j = k
            else:
                j += 1

        # --- Build question stem (without options) ---
        stem_parts: List[str] = [title_line]
        in_code_fence = False
        for pl in prompt_lines[1:]:
            if pl.strip().startswith("```"):
                in_code_fence = not in_code_fence
                stem_parts.append(pl.rstrip())
                continue
            if in_code_fence:
                stem_parts.append(pl.rstrip())
                continue
            # Skip option-like lines in the stem
            if re.match(r"^\s*[A-Z]\)\s+", pl):
                break
            # For matching, also skip numbered left items in the stem
            if qtype == "match" and re.match(r"^\s*\d+\)\s+", pl):
                continue
            if pl.strip():
                stem_parts.append(pl.strip())
        question_text = "\n".join(stem_parts)

        match_map = parse_match_answer(ans_raw) if qtype == "match" else None
        match_left: list[Option] | None = None
        match_right: list[Option] | None = None
        if qtype == "match":
            match_left, match_right = parse_match_columns(prompt_lines)
            # Fallback: if no right column parsed, reuse options list for right side
            if match_right is None or len(match_right) == 0:
                match_right = options or None

        q = Question(
            index=len(questions),
            file_qnum=file_qnum,
            qtype=qtype,
            title=title_line,
            prompt=question_text,
            answer_raw=ans_raw,
            match_map=match_map,
            match_left=match_left or None,
            options=options or None,
        )
        questions.append(q)

    return Quiz(title=title, meta_lines=meta_lines, questions=questions)
