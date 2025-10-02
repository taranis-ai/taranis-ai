from flask import Flask, Blueprint

from frontend.views.story_views import StoryView


def init(app: Flask):
    assess_bp = Blueprint("assess", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    assess_bp.add_url_rule("/assess", view_func=StoryView.as_view("assess"))
    assess_bp.add_url_rule("/story/<string:story_id>", view_func=StoryView.as_view("story"))

    app.register_blueprint(assess_bp)
