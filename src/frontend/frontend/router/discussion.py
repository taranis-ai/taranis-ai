from flask import Blueprint, Flask

from frontend.views import discussion_views


def init(app: Flask) -> None:
    blueprint = Blueprint("discussion", __name__, url_prefix=app.config["APPLICATION_ROOT"])
    blueprint.add_url_rule("/discussion", view_func=discussion_views.overview)
    blueprint.add_url_rule("/discussion/<kind>/<parent_id>", view_func=discussion_views.thread)
    blueprint.add_url_rule("/discussion/<kind>/<parent_id>/comments", view_func=discussion_views.post_comment, methods=["POST"])
    app.register_blueprint(blueprint)
