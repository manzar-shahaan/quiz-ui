"""Format checker for quiz markdown files.

Pure validation logic (no app state) so it can run as a CLI step:
    quiz-ui --check path/to/practice_test.md

The checks mirror what `app.quiz_parser.parse_quiz` and `app.grading` accept,
but strictly: anything the app would silently guess or drop is reported here
with a line/question reference so agents can fix the file before serving it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Lowercased tag -> canonical type. Mirrors quiz_parser's matching rules.
TYPE_ALIASES = {
    "mc": "mc",
    "m/c": "mc",
    "multi": "multi",
    "multiple": "multi",
    "multi-select": "multi",
    "t/f": "t/f",
    "tf": "t/f",
    "true/false": "t/f",
    "true false": "t/f",
    "match": "match",
    "matching": "match",
}

QUESTION_RE = re.compile(r"^\s*(\d+)\)\s*(.*)$")
TYPE_TAG_RE = re.compile(r"\(([^)]+)\)")
ANSWER_RE = re.compile(r"\banswer\s*:\s*(.*)$", re.IGNORECASE)
OPTION_RE = re.compile(r"^\s*([A-Z])\)")
MATCH_LEFT_RE = re.compile(r"^\s*(\d+)\)")
HEADING_RE = re.compile(r"^\s*#")


@dataclass
class _Block:
    line_no: int                 # 1-based line of the "N) ..." heading
    qnum: int
    head: str                     # text after "N) "
    prompt_lines: list[str]       # lines between the heading and Answer:
    answer_line_no: int | None
    answer_raw: str | None


def _split_blocks(lines: list[str]) -> list[_Block]:
    """Group lines into question blocks exactly like parse_quiz does:
    a numbered heading starts a block that runs until the next 'Answer:' line.
    """
    blocks: list[_Block] = []
    i = 0
    n = len(lines)
    while i < n:
        m = QUESTION_RE.match(lines[i])
        if not m:
            i += 1
            continue
        start = i
        qnum = int(m.group(1))
        head = m.group(2).strip()
        j = i + 1
        while j < n and not ANSWER_RE.search(lines[j]):
            j += 1
        if j >= n:
            # No Answer: line — the parser silently swallows the rest of the file.
            blocks.append(_Block(start + 1, qnum, head, lines[start + 1:], None, None))
            break
        ans = ANSWER_RE.search(lines[j])
        answer_raw = ans.group(1).strip() if ans else None
        blocks.append(
            _Block(start + 1, qnum, head, lines[start + 1:j], j + 1, answer_raw)
        )
        i = j + 1
    return blocks


def _flag_sequence(kind: str, labels: list[str], where: str, issues: list[str]) -> None:
    """Labels must run A, B, C... (or 1, 2, 3... when passed as strings)."""
    expected = [
        chr(ord("A") + k) if labels and labels[0].isalpha() else str(k + 1)
        for k in range(len(labels))
    ]
    if labels != expected:
        for k, (got, want) in enumerate(zip(labels, expected)):
            if got != want:
                issues.append(
                    f"{where}: {kind} labels out of sequence — expected '{want})' but found '{got})'"
                )
                return


def validate_quiz_text(text: str) -> tuple[list[str], int]:
    """Return (issues, question_count). An empty issue list means the file is good."""
    issues: list[str] = []
    lines = text.splitlines()

    if not any(HEADING_RE.match(line) for line in lines):
        issues.append("missing quiz title — the first '#' heading line is used as the title")

    blocks = _split_blocks(lines)
    if not blocks:
        issues.append("no questions found — expected numbered questions like '1) (MC) ...'")
        return issues, 0

    expected_qnum = 1
    for b in blocks:
        where = f"Q{b.qnum} (line {b.line_no})"

        if b.qnum != expected_qnum:
            issues.append(
                f"{where}: question number {b.qnum} is out of sequence (expected {expected_qnum})"
            )
        expected_qnum = b.qnum + 1

        type_tag = TYPE_TAG_RE.search(b.head)
        qtype: str | None
        if not type_tag:
            issues.append(
                f"{where}: missing question type tag — put (MC), (Multi), (T/F) or (Match) after the number"
            )
            qtype = None
        else:
            qtype = TYPE_ALIASES.get(type_tag.group(1).strip().lower())
            if qtype is None:
                issues.append(
                    f"{where}: unknown type tag '({type_tag.group(1)})' — "
                    f"supported: (MC), (Multi), (T/F), (Match)"
                )

        if b.answer_raw is None:
            issues.append(
                f"{where}: no 'Answer:' line — every question must end with 'Answer: ...'"
            )

        # Collect option letters (and match left numbers) from the block body.
        opt_labels: list[str] = []
        match_left: list[str] = []
        for line in b.prompt_lines:
            mo = OPTION_RE.match(line)
            if mo:
                opt_labels.append(mo.group(1))
            elif qtype == "match":
                ml = MATCH_LEFT_RE.match(line)
                if ml:
                    match_left.append(ml.group(1))

        if qtype in ("mc", "multi"):
            if len(opt_labels) < 2:
                issues.append(
                    f"{where}: {'MC' if qtype == 'mc' else 'Multi'} question needs at least "
                    f"two options (A), B), ...)"
                )
            _flag_sequence("option", opt_labels, where, issues)

            if b.answer_raw is not None and opt_labels:
                if qtype == "mc":
                    if not re.fullmatch(r"[A-Za-z]", b.answer_raw):
                        issues.append(
                            f"{where}: MC answer must be a single letter like 'A', got '{b.answer_raw}'"
                        )
                    elif b.answer_raw.upper() not in opt_labels:
                        issues.append(
                            f"{where}: MC answer '{b.answer_raw}' does not match any option "
                            f"{opt_labels}"
                        )
                else:
                    letters = [part.strip() for part in b.answer_raw.split(",")]
                    if not all(re.fullmatch(r"[A-Za-z]", x) for x in letters):
                        issues.append(
                            f"{where}: Multi answer must be comma-separated letters like 'A,C', "
                            f"got '{b.answer_raw}'"
                        )
                    else:
                        uppers = [x.upper() for x in letters]
                        if len(set(uppers)) != len(uppers):
                            issues.append(
                                f"{where}: Multi answer repeats a letter: '{b.answer_raw}'"
                            )
                        unknown = [x for x in uppers if x not in opt_labels]
                        if unknown:
                            issues.append(
                                f"{where}: Multi answer letters {unknown} not among the options "
                                f"{opt_labels}"
                            )

        elif qtype == "t/f":
            if b.answer_raw is not None and b.answer_raw.lower() not in ("t", "f", "true", "false"):
                issues.append(
                    f"{where}: T/F answer must be T or F, got '{b.answer_raw}'"
                )

        elif qtype == "match":
            if len(match_left) < 1:
                issues.append(
                    f"{where}: Match question needs numbered left items (1), 2), ...)"
                )
            _flag_sequence("match left", match_left, where, issues)
            if len(opt_labels) < 2:
                issues.append(
                    f"{where}: Match question needs at least two lettered right options "
                    f"(A), B), ...)"
                )
            _flag_sequence("option", opt_labels, where, issues)

            if b.answer_raw is not None and match_left and opt_labels:
                pairs: list[tuple[str, str]] = []
                malformed = False
                for part in b.answer_raw.split(","):
                    pm = re.fullmatch(r"(\d+)\s*-\s*([A-Za-z])", part.strip())
                    if not pm:
                        malformed = True
                        break
                    pairs.append((pm.group(1), pm.group(2).upper()))
                if malformed:
                    issues.append(
                        f"{where}: Match answer must be number-letter pairs like '1-A,2-B', "
                        f"got '{b.answer_raw}'"
                    )
                else:
                    numbers = [p[0] for p in pairs]
                    letters = [p[1] for p in pairs]
                    if len(set(numbers)) != len(numbers):
                        issues.append(
                            f"{where}: Match answer maps a left item more than once"
                        )
                    if len(set(letters)) != len(letters):
                        issues.append(
                            f"{where}: Match answer uses the same right letter twice"
                        )
                    unknown_nums = sorted({x for x in numbers if x not in match_left})
                    if unknown_nums:
                        issues.append(
                            f"{where}: Match answer numbers {unknown_nums} not among left items "
                            f"{match_left}"
                        )
                    unknown_letters = sorted({x for x in letters if x not in opt_labels})
                    if unknown_letters:
                        issues.append(
                            f"{where}: Match answer letters {unknown_letters} not among the right "
                            f"options {opt_labels}"
                        )
                    missing = [x for x in match_left if x not in numbers]
                    if missing:
                        issues.append(
                            f"{where}: Match answer does not cover left items {missing}"
                        )

    return issues, len(blocks)


def check_quiz_file(path: Path) -> tuple[list[str], int]:
    """Validate a quiz file; also cross-check the real parser round-trips the
    same question count when no format issues were found."""
    text = path.read_text(encoding="utf-8")
    issues, count = validate_quiz_text(text)

    if not issues:
        from .quiz_parser import parse_quiz

        parsed = parse_quiz(path)
        if len(parsed.questions) != count:
            issues.append(
                f"parser mismatch: checker found {count} questions but the app parser found "
                f"{len(parsed.questions)} — file needs manual review"
            )
    return issues, count
