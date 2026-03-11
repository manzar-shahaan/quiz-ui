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


def main():
    parser = argparse.ArgumentParser(
        description="Run quiz practice server for a given practice_test.md"
    )
    parser.add_argument(
        "quiz_file",
        nargs="?",
        type=Path,
        help="Path to the practice_test.md file",
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
    args = parser.parse_args()

    if args.format:
        _print_format()
        return

    if not args.quiz_file:
        parser.error("quiz_file is required unless you pass --format")

    if not args.quiz_file.exists():
        raise SystemExit(f"Quiz file not found: {args.quiz_file}")

    app = create_app(quiz_path=args.quiz_file)

    # Debug True for dev; change if you want
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
