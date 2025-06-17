from flask import Flask, redirect, url_for
from flask_htmx import HTMX
from flask.json.provider import DefaultJSONProvider
from pydantic import BaseModel
import frontend.filters as filters_module
from frontend.config import Config
from frontend.views.base_view import BaseView

from heroicons.jinja import (
    heroicon_micro,
    heroicon_mini,
    heroicon_outline,
    heroicon_solid,
)


def handle_unauthorized(e):
    return redirect(url_for("base.login"), code=302)


class TaranisJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        transformed_obj = self._transform(obj)
        return super().dumps(transformed_obj, **kwargs)

    def _transform(self, obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump(exclude_none=True)
        elif isinstance(obj, list):
            return [self._transform(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._transform(value) for key, value in obj.items()}
        return obj


def index_redirect():
    return redirect(Config.APPLICATION_ROOT, code=302)


def jinja_setup(app: Flask):
    for name in filters_module.__all__:
        app.jinja_env.filters[name] = getattr(filters_module, name)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.globals.update(
        {
            "heroicon_micro": heroicon_micro,
            "heroicon_mini": heroicon_mini,
            "heroicon_outline": heroicon_outline,
            "heroicon_solid": heroicon_solid,
            "views": dict(sorted(BaseView._registry.items(), key=lambda item: (getattr(item[1], "_index", float("inf")), item[0]))),
        }
    )

    if Config.APPLICATION_ROOT != "/":
        app.add_url_rule("/", view_func=index_redirect)


def init(app: Flask):
    app.json_provider_class = TaranisJSONProvider
    app.json = app.json_provider_class(app)
    HTMX(app)
    app.register_error_handler(401, handle_unauthorized)

    app.url_map.strict_slashes = False

    jinja_setup(app)
