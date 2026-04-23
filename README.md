<p align="center">
  <img src="assets/icon.png" width="96" alt="Quiz UI logo">
</p>

# Quiz UI

A lightweight local quiz app that renders multiple-choice practice tests from a Markdown file. Answer questions in your browser, submit, and get a detailed results page with per-question feedback. A feedback file is written next to your quiz file so you can focus follow-up study on weak areas.

---

## Download (no setup required)

Pre-built launchers are available on the [Releases](../../releases) page:

| Platform | File |
|----------|------|
| Windows  | `QuizLauncher.exe` |
| macOS    | `QuizLauncher-macos.zip` (unzip → double-click) |
| Linux    | `QuizLauncher` (mark executable → run) |

The launcher lets you pick a `.md` quiz file through a file picker, starts the server automatically, and opens it in your browser — no terminal needed.

> **macOS note:** First launch may be blocked by Gatekeeper. Right-click the app → Open → Open to allow it.

> **Linux note:** After downloading, make the file executable: `chmod +x QuizLauncher`

---

## For developers / CLI use

### Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 run_quiz_server.py /path/to/practice_test.md
```

Then open `http://127.0.0.1:8000` in your browser.

### Install as a CLI tool

```bash
pip install .
quiz-ui /path/to/practice_test.md
```

Options:

```
quiz-ui --format          # Print the quiz file format guide
quiz-ui file.md --port 9000   # Use a different port
```

### Run the GUI launcher from source

```bash
pip install -r requirements.txt
python launcher.py
```

---

## Quiz file format

Four question types are supported: `(MC)`, `(Multi)`, `(T/F)`, `(Match)`.

```md
# Example Practice Quiz
- Topic: Sample

1) (MC) Which HTTP method retrieves data?
   A) GET
   B) POST
   C) DELETE
Answer: A

2) (T/F) The sky is green.
Answer: F

3) (Multi) Which are programming languages?
   A) Python
   B) HTML
   C) Java
   D) CSS
Answer: A,C

4) (Match) Match the term to its description.
   1) Primary key
   2) Foreign key
   A) Uniquely identifies a row
   B) References another table
Answer: 1-A,2-B
```

See [QUIZ_FORMAT.md](QUIZ_FORMAT.md) for the full spec including strict formatting rules.

---

## Features

- **Question types:** single-choice, multi-select, true/false, matching
- **Timer:** optional countdown with auto-submit on expiry
- **Code blocks:** fenced ` ``` ` blocks render with syntax highlighting and a language label
- **Results page:** per-question breakdown with correct/incorrect indicators
- **Feedback file:** written next to the quiz file after submission — lists incorrect and partial questions for focused follow-up

---

## Feedback output

After submitting, a file is written into the same folder as the quiz:

- Filename: `test {x} feedback {YYYY-MM-DD HH-MM-SS}.md`
- Content: overall score + a "Questions to review" section for incorrect/partial answers

---

## Notes

- State is in-memory. Restarting the server clears all answers.
- Multiple quizzes can run simultaneously on different ports via the GUI launcher.
- This project is not affiliated with any LMS vendor.
