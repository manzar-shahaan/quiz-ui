#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from app import create_app


def _print_format():
    """
    Print the authoritative quiz format guide.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here / "QUIZ_FORMAT.md",
        here.parent / "QUIZ_FORMAT.md",
        Path.cwd() / "QUIZ_FORMAT.md",
    ]
    for path in candidates:
        if path.exists():
            sys.stdout.write(path.read_text(encoding="utf-8"))
            return

    # Fallback if file not packaged
    sys.stdout.write(
        "# Quiz Markdown Format (summary)\n"
        "- Title: first heading line starting with #\n"
        "- Questions: numbered 1), 2), ... with a type tag in parentheses\n"
        "- Supported types:\n"
        "  - (MC) single-answer multiple choice; answer like A\n"
        "  - (Multi) multi-select; answer like A,C\n"
        "  - (T/F) true/false; answer T or F\n"
        "  - (Match) matching; answer like 1-A,2-B\n"
        "- Options: label as A) B) C)... directly under the question\n"
        "- Answer line: starts with 'Answer:' immediately after the options block\n"
    )


def _run_check(quiz_file: Path) -> int:
    """Validate a quiz markdown file and print OK or the issues found.

    Returns the process exit code (0 = valid, 1 = issues).
    """
    from app.checker import check_quiz_file

    if not quiz_file.exists():
        print(f"ERROR: quiz file not found: {quiz_file}", file=sys.stderr)
        return 1

    try:
        issues, count = check_quiz_file(quiz_file)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: could not read {quiz_file}: {exc}", file=sys.stderr)
        return 1

    if issues:
        plural = "" if len(issues) == 1 else "s"
        print(
            f"ERROR: {quiz_file} failed format check ({len(issues)} issue{plural}):",
            file=sys.stderr,
        )
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print(f"OK: {quiz_file} passed format check ({count} questions)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run a practice-quiz server for a practice_test.md file, or validate "
            "a quiz file's format with --check"
        )
    )
    parser.add_argument(
        "quiz_file",
        nargs="?",
        type=Path,
        help="Path to the practice_test.md file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the quiz file's format (title, question numbers, type tags, options, answers) and exit: prints OK or the issues found",
    )
    parser.add_argument(
        "--format",
        action="store_true",
        help="Print the quiz Markdown format guide and exit",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host to bind (default 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port to bind (default 8000)",
    )
    parser.add_argument(
        "--launcher",
        action="store_true",
        help=argparse.SUPPRESS,  # internal flag set by the GUI launcher
    )
    args = parser.parse_args()

    if args.check:
        if not args.quiz_file:
            parser.error("quiz_file is required with --check")
        raise SystemExit(_run_check(args.quiz_file))

    if args.format:
        _print_format()
        return

    if not args.quiz_file:
        parser.error("quiz_file is required unless you pass --format or --check")

    if not args.quiz_file.exists():
        raise SystemExit(f"Quiz file not found: {args.quiz_file}")

    app = create_app(quiz_path=args.quiz_file)

    # Launcher mode disables the reloader so the GUI can track the process cleanly
    app.run(host=args.host, port=args.port, debug=not args.launcher, use_reloader=not args.launcher)


if __name__ == "__main__":
    main()
