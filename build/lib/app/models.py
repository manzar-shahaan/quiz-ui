from dataclasses import dataclass
from typing import List, Dict, Literal, Optional


QuestionType = Literal["match", "t/f", "mc", "multi"]


@dataclass
class Option:
    label: str   # "A", "B", "C", ...
    text: str    # "Planning", "Organizing", ...


@dataclass
class Question:
    index: int                   # 0-based index in quiz
    file_qnum: int               # original number in .md (1,2,3,...)
    qtype: QuestionType
    title: str                   # short description from first line
    prompt: str                  # question text (without the options)
    answer_raw: str              # raw "Answer: ..." content
    match_map: Optional[Dict[str, str]] = None  # for match only
    match_left: Optional[List[Option]] = None   # left-hand items for match
    options: Optional[List[Option]] = None      # for MC / Multi (and possibly Match)


@dataclass
class Quiz:
    title: str
    meta_lines: List[str]
    questions: List[Question]
