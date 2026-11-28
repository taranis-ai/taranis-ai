import yaml
from flask import Blueprint, Response, send_from_directory
from flask.views import MethodView
from flask_openapi import OpenAPI

from core.config import Config
from core.managers.data_manager import get_default_json


class DefaultWordLists(MethodView):
    def get(self):
        return send_from_directory(get_default_json("default_word_lists.json"), "default_word_lists.json")


def initialize(app: OpenAPI):
    static_bp = Blueprint("static", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/static")

    static_bp.add_url_rule("/default_word_lists.json", view_func=DefaultWordLists.as_view("default_word_lists"))

    @static_bp.get("/openapi3_1.yaml")
    def openapi3():
        return Response(yaml.safe_dump(app.api_doc, sort_keys=False), mimetype="application/yaml")

    app.register_blueprint(static_bp)
