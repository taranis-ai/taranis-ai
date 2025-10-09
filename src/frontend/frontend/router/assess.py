from flask import Flask, Blueprint

from frontend.views.story_views import StoryView


def init(app: Flask):
    assess_bp = Blueprint("assess", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    assess_bp.add_url_rule("/assess", view_func=StoryView.as_view("assess"))
    assess_bp.add_url_rule("/story/<string:story_id>", view_func=StoryView.as_view("story"))
    assess_bp.add_url_rule("/story/<string:story_id>/edit", view_func=StoryView.as_view("story_edit"))
    assess_bp.add_url_rule("/story/sharing", view_func=StoryView.get_sharing_dialog, methods=["GET"], endpoint="share_story")
    assess_bp.add_url_rule("/story/sharing", view_func=StoryView.submit_sharing_dialog, methods=["POST"], endpoint="submit_share_story")
    assess_bp.add_url_rule("/stories/mark-read", view_func=StoryView.bulk_mark_read, methods=["POST"], endpoint="bulk_mark_read")
    assess_bp.add_url_rule(
        "/stories/mark-important", view_func=StoryView.bulk_mark_important, methods=["POST"], endpoint="bulk_mark_important"
    )

    app.register_blueprint(assess_bp)
