from pathlib import Path
from flask import Flask

from . import quiz_parser


def create_app(quiz_path: Path) -> Flask:
    # Uses default static and template folders bundled inside the package
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["QUIZ_PATH"] = str(quiz_path.resolve())
    app.config["QUIZ_FILENAME"] = quiz_path.name

    quiz = quiz_parser.parse_quiz(quiz_path)
    app.config["QUIZ"] = quiz

    # DEBUG: print how many questions we actually loaded
    print(f"[quiz] Loaded {len(quiz.questions)} questions from {quiz_path}")

    @app.context_processor
    def _inject_globals():
        return {"quiz_filename": app.config.get("QUIZ_FILENAME")}

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
