from pathlib import Path
from flask import Flask, send_from_directory
from flask.views import MethodView

from core.log import logger


def get_git_root() -> Path:
    """Return the git root directory of the current repo."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Git root not found")


def get_frontend_dist() -> Path:
    """Return the path to the frontend dist folder."""
    return get_git_root() / "src" / "gui" / "dist"


class Frontend(MethodView):
    def get(self, filename="index.html"):
        try:
            return send_from_directory(get_frontend_dist(), filename)
        except Exception as e:
            logger.warning(f"Error: {e}")
            return send_from_directory(get_frontend_dist(), "index.html")


def initialize(app: Flask):
    logger.info("Initializing frontend for e2e tests")
    app.add_url_rule("/<path:filename>", view_func=Frontend.as_view("frontend"))
    app.add_url_rule("/", view_func=Frontend.as_view("frontend_"))
