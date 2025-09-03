from flask import Flask, Blueprint

from frontend.views.publish_views import PublishView


def init(app: Flask):
    publish_bp = Blueprint("publish", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}/publish")

    publish_bp.add_url_rule("/", view_func=PublishView.as_view("publish"))

    app.register_blueprint(publish_bp)
