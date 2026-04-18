import html as _html_lib
import re as _re_lib
from pathlib import Path
from flask import Flask

from . import quiz_parser


def _render_prompt(text: str) -> str:
    """Convert markdown ``` code fences to <pre><code> blocks; escape remaining text."""
    fence_re = _re_lib.compile(r'```(\w*)\n(.*?)```', _re_lib.DOTALL)
    result = []
    last_end = 0
    for m in fence_re.finditer(text):
        before = text[last_end:m.start()]
        if before:
            result.append(f'<span class="bs-qtext-prose">{_html_lib.escape(before)}</span>')
        lang = m.group(1).strip()
        code = m.group(2)
        if lang:
            result.append(
                f'<div class="bs-code-wrapper">'
                f'<span class="bs-code-lang">{_html_lib.escape(lang)}</span>'
                f'<pre class="bs-code-block"><code class="language-{lang}">{_html_lib.escape(code)}</code></pre>'
                f'</div>'
            )
        else:
            result.append(
                f'<pre class="bs-code-block"><code>{_html_lib.escape(code)}</code></pre>'
            )
        last_end = m.end()
    remainder = text[last_end:]
    if remainder:
        result.append(f'<span class="bs-qtext-prose">{_html_lib.escape(remainder)}</span>')
    return ''.join(result)


def create_app(quiz_path: Path) -> Flask:
    # Uses default static and template folders bundled inside the package
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"
    app.config["QUIZ_PATH"] = str(quiz_path.resolve())
    app.config["QUIZ_FILENAME"] = quiz_path.name

    quiz = quiz_parser.parse_quiz(quiz_path)
    app.config["QUIZ"] = quiz

    app.jinja_env.filters['render_prompt'] = _render_prompt

    # DEBUG: print how many questions we actually loaded
    print(f"[quiz] Loaded {len(quiz.questions)} questions from {quiz_path}")

    @app.context_processor
    def _inject_globals():
        return {"quiz_filename": app.config.get("QUIZ_FILENAME")}

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    return app
