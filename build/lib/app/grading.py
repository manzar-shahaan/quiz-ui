import re
from typing import Dict, Tuple, Optional, Set

from .models import Question


def _letters_set(s: str) -> Set[str]:
    return set(re.findall(r"[A-Z]", s.upper()))


def grade_question(
    question: Question,
    user_answer: str,
) -> Tuple[float, str]:
    """
    Returns (score_in_[0,1], correct_display_string).
    """
    qtype = question.qtype
    ans_raw = question.answer_raw

    if qtype == "t/f":
        correct_bool = ans_raw.strip().lower().startswith("t")
        correct_disp = "True" if correct_bool else "False"
        user_norm = user_answer.strip().lower()
        if user_norm in ("t", "true"):
            user_bool = True
        elif user_norm in ("f", "false"):
            user_bool = False
        else:
            return 0.0, correct_disp
        return (1.0 if user_bool == correct_bool else 0.0), correct_disp

    if qtype == "mc":
        m = re.search(r"\b([A-Z])\b", ans_raw.upper())
        correct_letter = m.group(1) if m else ans_raw
        user_letters = _letters_set(user_answer)
        # Expect exactly one letter
        if len(user_letters) != 1:
            return 0.0, correct_letter
        (user_letter,) = user_letters
        return (1.0 if user_letter == correct_letter else 0.0), correct_letter

    if qtype == "match":
        correct_map: Dict[str, str] = question.match_map or {}
        pairs = re.findall(r"(\d+)\s*-\s*([A-Z])", user_answer.upper())
        user_map = {num: letter for num, letter in pairs}
        if set(user_map.keys()) != set(correct_map.keys()):
            score = 0.0
        else:
            score = 1.0 if all(user_map[k] == v for k, v in correct_map.items()) else 0.0
        ordered = sorted(correct_map.keys(), key=lambda x: int(x))
        correct_disp = ", ".join(f"{k}-{correct_map[k]}" for k in ordered)
        return score, correct_disp

    # multi-select with partial credit
    correct_set = _letters_set(ans_raw)
    user_set = _letters_set(user_answer)
    if not correct_set or not user_set:
        return 0.0, ",".join(sorted(correct_set))

    n_correct = len(correct_set & user_set)
    n_wrong = len(user_set - correct_set)
    score = max(0.0, (n_correct - n_wrong) / len(correct_set))
    correct_disp = ",".join(sorted(correct_set))
    return score, correct_disp
