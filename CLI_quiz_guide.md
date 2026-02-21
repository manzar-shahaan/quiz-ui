# Course Quiz System (Windows guide)

This guide explains what each tool does, how your course folder is structured, how to generate practice tests with opencode, and how to run them in `quiz_ui`.

The single most important rule: do everything from the course folder (the folder that contains `AGENTS.md`).

## What each thing is (plain language)

Terminal / Windows Terminal
- The app that runs command-line commands. On Windows, the “Terminal” app usually opens a PowerShell tab by default.

PowerShell (the default shell)
- The command language inside Windows Terminal. You type commands and press Enter.
- When this guide shows commands, you can run them in PowerShell.

Current folder (a.k.a. “working directory”)
- The folder your terminal is currently “in”. Many tools (including opencode) look for files relative to this folder.
- If you run opencode from the wrong folder, it may not see `AGENTS.md` and will produce inconsistent results.

opencode
- The CLI agent you talk to. It reads `AGENTS.md` in your current folder (and sometimes parent folders) to learn the project rules.
- In this setup, opencode generates/edit quiz markdown files inside `practice_tests\`.

`AGENTS.md`
- In general: a project-local instruction file that tells opencode how to behave for a specific workspace (naming, workflow, output formats, priorities, do/don't rules).
- In this course setup: it describes the quiz markdown format that `quiz_ui` can parse, plus any course-specific conventions (where quizzes live, how to name them, what sources to use).

`quiz_ui`
- A small local web server (Flask) that reads a quiz markdown file, parses questions, and serves a quiz website.
- It never edits your quiz file; it only reads it (but it can write a separate feedback `.md` next to the quiz after you submit).

Browser (Chrome/Edge/Firefox)
- Shows the quiz website.
- The quiz website only works while the server is running in your terminal.

## How the pieces fit together (mental model)

1) You collect source material in the course folder (slides, schedules, notes).
2) You run opencode from the course folder.
3) opencode reads `AGENTS.md` and writes a quiz markdown file to `practice_tests\...`.
4) You run `quiz_ui` and point it at that markdown file.
5) `quiz_ui` starts a local server; your browser connects to it and you take the quiz.

Important: the terminal tab running `quiz_ui` must stay open. If you close it, the quiz website stops working.

## Your per-course folder setup (copy this per class)

One course = one folder. Inside that course folder:

- `AGENTS.md` (course-specific instructions + quiz format)
- `quiz_ui\` (the runner app)
- `practice_tests\` (all generated quizzes, `*.md`)
- Optional: `slides\`, `course_info\`, `notes\`, etc.

Why this matters:
- You can copy the whole course folder to start a new course.
- You always know where quizzes live.
- opencode sees `AGENTS.md` automatically when run from the course folder.

What opencode should be able to reference in prompts:
- `AGENTS.md` (format + rules)
- `practice_tests\` (where to write output)
- `slides\` / `course_info\` / `notes\` (what to base questions on)

## How to open a terminal in the right place (do this every time)

Recommended method (least error-prone):

1) Open File Explorer.
2) Go to your course folder (the one that contains `AGENTS.md`).
3) Click the address bar, type `wt`, press Enter.
   This opens Windows Terminal already set to that folder.

Quick self-check (PowerShell):

```powershell
Get-Location
```

You should see the path to your course folder.

## Workflow A: generate a practice test (opencode)

Goal: create a quiz markdown file that matches the rules in `AGENTS.md`, saved under `practice_tests\`.

1) Ensure your terminal is in the course folder.
2) Start opencode (whatever command you normally use to launch it).
3) Tell it what to generate and where to write it (include an explicit path under `practice_tests\`).

Recommended file naming:
- Put everything in `practice_tests\`
- Use a stable “current” file if you like re-running the same filename:
  - `practice_tests\practice_test.md`
- Or use topic/date names if you want history:
  - `practice_tests\practice_test_week03.md`
  - `practice_tests\practice_test_subnetting_2026-01-23.md`

Practical prompting tips (so the output works in `quiz_ui`):
- Explicitly say: “Use the quiz markdown format from `AGENTS.md` exactly.”
- Require an `Answer:` line immediately after each question block.
- Don’t put all answers in one section at the end; `quiz_ui` expects the `Answer:` right after each question.
- Use `@` to attach/reference specific files or folders in your prompt (for example `@slides\` or `@course_info\week03_outline.md`) so opencode focuses on the right material.
- If you want variety, ask for a mix (MCQ, multi-select, T/F, matching) but still require the correct formatting.

Example prompt patterns (edit the topic to your course):

```text
Read the course sources in slides\ and course_info\ and generate a practice test in the exact format described in AGENTS.md.
Write the output to practice_tests\practice_test_week03.md.
Focus on: subnetting, DNS, and common exam traps. Put `Answer: ...` right after each question.
```

```text
Update practice_tests\practice_test.md to be harder.
Keep the exact AGENTS.md format. Replace 30% of questions with new ones.
Include 5 matching questions and 5 multi-select questions.
```

If the quiz doesn’t parse, don’t hand-edit randomly first: re-check `AGENTS.md` and regenerate with a tighter prompt.

## Workflow B: run a quiz (quiz_ui)

Goal: start the local server, then take the quiz in your browser.

From the course folder, run:

```bat
python quiz_ui\run_quiz_server.py "practice_tests\practice_test.md"
```

If `python` is not recognized on your machine, use:

```bat
py quiz_ui\run_quiz_server.py "practice_tests\practice_test.md"
```

Now:

1) Leave that terminal tab/window open.
   The quiz website only works while this command is running.
2) Open your browser to:
   http://127.0.0.1:8000
3) Take the quiz.
4) When done, stop the server with Ctrl+C in the same terminal tab.

Notes:
- Attempts are in-memory. Stopping/restarting the server clears answers.
- If you edit/regenerate the `*.md`, restart the server to reload the quiz.
- After submit, `quiz_ui` writes a feedback markdown file in the same folder as the quiz file.

## Troubleshooting (common problems -> fastest fix)

"opencode produced weird format" / quiz won’t parse
- Cause: opencode didn’t apply `AGENTS.md` rules or the prompt was too loose.
- Fix: open terminal in the course folder, rerun opencode, explicitly reference `AGENTS.md` and `practice_tests\...` in your request.

"The system cannot find the path specified" / file not found
- Cause: wrong relative path or wrong working directory.
- Fix: confirm you are in the course folder (`Get-Location`). Confirm the file exists in `practice_tests\`.
- Tip: you can always pass a full path to the quiz file.

"python is not recognized" (or similar)
- Fix: use `py` instead of `python`, or ensure Python is installed and on PATH.

Browser says it can’t reach the site
- Cause: the server command is not running anymore.
- Fix: look at the terminal tab; if it stopped/closed/errored, re-run the server command and keep that tab open.

Port 8000 already in use
- Cause: an old server is still running, or another app uses that port.
- Fix: close the other server terminal tab, or stop it with Ctrl+C. Then re-run.

Paths with spaces
- Fix: always wrap paths in quotes: `"C:\Some Folder\practice_tests\practice_test.md"`.

## Replicating this setup for another course

1) Create a new course folder.
2) Copy in:
   - `quiz_ui\`
   - `AGENTS.md` (then edit it to match the new course)
3) Create an empty `practice_tests\` folder.
4) Validate quickly:
   - Run opencode from the new course folder.
   - Generate `practice_tests\practice_test.md`.
   - Run `python quiz_ui\run_quiz_server.py "practice_tests\practice_test.md"` and confirm it loads.

If you follow the “always work from the course folder” rule, 90% of the usual CLI/path issues disappear.
