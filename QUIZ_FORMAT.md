# Quiz Markdown Format (authoritative)

Use this template in any repo. Copy/symlink this file next to your `practice_test.md` to keep formatting consistent.

## File structure (required)
- First line: `#` heading = quiz title.
- Optional metadata: bullet list immediately after the title (e.g., `- Topic: Networking`).
- Questions: numbered `1)`, `2)`, ... with no blank lines between question parts.
- Answer line: starts with `Answer:` directly under the question body.

## Supported question types and syntax

**Supported types (exact labels in parentheses):**
- `(MC)` single-answer multiple choice; answers use one letter like `A`.
- `(Multi)` multiple-select; answers use comma-separated letters like `A,C`.
- `(T/F)` true/false; answers use `T` or `F`.
- `(Match)` matching left numbers to right letters; answers use `number-letter` pairs like `1-A,2-B`.

1) Multiple choice (single answer)
```
1) (MC) Question text?
   A) Option
   B) Option
   C) Option
Answer: A
```

2) Multiple select (multiple answers)
```
2) (Multi) Question text?
   A) Option
   B) Option
   C) Option
   D) Option
Answer: A,C
```

3) True/False
```
3) (T/F) Statement text.
Answer: T
```
Use `T` or `F` only.

4) Matching
```
4) (Match) Match each item.
   1) Left item one
   2) Left item two
   A) Right option one
   B) Right option two
Answer: 1-A,2-B
```
Pairs use `number-letter` separated by commas.

## Formatting rules (strict)
- Options must be labeled `A)`, `B)`, `C)...` exactly.
- Matching left side must be numbered `1)`, `2)...`; right side must be lettered `A)`, `B)...`.
- Answers are case-insensitive but must follow the shown patterns (`A`, `A,C`, `T`, `1-A,2-B`).
- No blank lines between options and the Answer line.
- Keep question text and options on separate lines; do not indent the Answer line more than two spaces.

## Unsupported (do not use)
- Free-text or short-answer questions.
- Numeric fill-in answers (e.g., `42`).
- Code-evaluated questions or embedded test cases.
- Image-based options.
- Nested sub-questions inside one number.

## Quick scaffold (copy/paste)
```
# Your Quiz Title
- Topic: ...
- Difficulty: ...

1) (MC) ...?
   A) ...
   B) ...
   C) ...
Answer: A

2) (Multi) ...?
   A) ...
   B) ...
   C) ...
   D) ...
Answer: A,C

3) (T/F) ...
Answer: T

4) (Match) ...
   1) ...
   2) ...
   A) ...
   B) ...
Answer: 1-A,2-B
```

## Usage pattern
- Author a quiz file following this format.
- Open it via the GUI launcher (click **+ Add Quiz**) or run `quiz-ui /path/to/practice_test.md` from the terminal.
- If parser errors occur, re-check against the patterns above.
