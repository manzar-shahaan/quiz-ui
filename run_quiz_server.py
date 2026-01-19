#!/usr/bin/env python3
import argparse
from pathlib import Path

from app import create_app


def main():
    parser = argparse.ArgumentParser(
        description="Run quiz practice server for a given practice_test.md"
    )
    parser.add_argument(
        "quiz_file",
        type=Path,
        help="Path to the practice_test.md file",
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

    if not args.quiz_file.exists():
        raise SystemExit(f"Quiz file not found: {args.quiz_file}")

    app = create_app(quiz_path=args.quiz_file)

    # Debug True for dev; change if you want
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
