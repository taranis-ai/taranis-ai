from admin.filters import human_readable_trigger

from flask import Flask
from heroicons.jinja import (
    heroicon_micro,
    heroicon_mini,
    heroicon_outline,
    heroicon_solid,
)


def jinja_setup(app: Flask):
    app.jinja_env.filters["human_readable"] = human_readable_trigger
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.globals.update(
        {
            "heroicon_micro": heroicon_micro,
            "heroicon_mini": heroicon_mini,
            "heroicon_outline": heroicon_outline,
            "heroicon_solid": heroicon_solid,
        }
    )
