from flask import Flask, send_from_directory, Blueprint
from flask.views import MethodView
from core.config import Config
from core.managers.data_manager import get_default_json


class DefaultSources(MethodView):
    def get(self):
        return send_from_directory(get_default_json("default_sources.json"), "default_sources.json")


class DefaultWordLists(MethodView):
    def get(self):
        return send_from_directory(get_default_json("default_word_lists.json"), "default_word_lists.json")


class OpenAPI3_1(MethodView):
    def get(self):
        return send_from_directory("static", "openapi3_1.yaml")


def initialize(app: Flask):
    static_bp = Blueprint("static", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/static")

    static_bp.add_url_rule("/default_sources.json", view_func=DefaultSources.as_view("default_source"))
    static_bp.add_url_rule("/default_word_lists.json", view_func=DefaultWordLists.as_view("default_word_lists"))
    static_bp.add_url_rule("/openapi3_1.yaml", view_func=OpenAPI3_1.as_view("openapi3_1"))

    app.register_blueprint(static_bp)
