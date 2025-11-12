from flask import Blueprint, Flask

from frontend.views.story_views import StoryView


def init(app: Flask):
    assess_bp = Blueprint("assess", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    assess_bp.add_url_rule("/assess", view_func=StoryView.as_view("assess"))
    assess_bp.add_url_rule("/story/<string:story_id>", view_func=StoryView.story_view, methods=["GET"], endpoint="story")
    assess_bp.add_url_rule(
        "/story/<string:story_id>", view_func=StoryView.patch_story, methods=["POST", "PUT", "PATCH"], endpoint="story_update"
    )
    assess_bp.add_url_rule("/story/<string:story_id>/edit", view_func=StoryView.as_view("story_edit"))
    assess_bp.add_url_rule(
        "/story/<string:story_id>/bots", view_func=StoryView.trigger_bot_action, methods=["POST"], endpoint="story_trigger_bot"
    )
    assess_bp.add_url_rule(
        "/news-item/<string:news_item_id>", view_func=StoryView.create_news_item, methods=["POST"], endpoint="create_news_item"
    )
    assess_bp.add_url_rule("/news-item/<string:news_item_id>", view_func=StoryView.news_item_view, methods=["GET"], endpoint="get_news_item")
    assess_bp.add_url_rule("/search", view_func=StoryView.get_search_dialog, methods=["GET"], endpoint="search_stories")
    assess_bp.add_url_rule("/search", view_func=StoryView.submit_search_dialog, methods=["POST"], endpoint="submit_search_stories")
    assess_bp.add_url_rule("/story/sharing", view_func=StoryView.get_sharing_dialog, methods=["GET"], endpoint="share_story")
    assess_bp.add_url_rule("/story/sharing", view_func=StoryView.submit_sharing_dialog, methods=["POST"], endpoint="submit_share_story")
    assess_bp.add_url_rule("/story/report", view_func=StoryView.get_report_dialog, methods=["GET"], endpoint="report_story")
    assess_bp.add_url_rule("/story/report", view_func=StoryView.submit_report_dialog, methods=["POST"], endpoint="submit_report_story")
    assess_bp.add_url_rule("/story/cluster", view_func=StoryView.get_cluster_dialog, methods=["GET"], endpoint="cluster_story")
    assess_bp.add_url_rule("/story/cluster", view_func=StoryView.submit_cluster_dialog, methods=["POST"], endpoint="submit_cluster_story")
    assess_bp.add_url_rule("/tags", view_func=StoryView.get_tags, methods=["GET"], endpoint="get_tags")

    assess_bp.add_url_rule("/stories/bulk_action", view_func=StoryView.bulk_action, methods=["POST"], endpoint="bulk_action")

    app.register_blueprint(assess_bp)
