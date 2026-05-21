from flask import Blueprint, Flask

from frontend.views.collaboration_views import CollaborationView


def init(app: Flask):
    collaboration_bp = Blueprint("collaboration", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    collaboration_bp.add_url_rule("/collaboration", view_func=CollaborationView.workspace, methods=["GET"], endpoint="workspace")
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>",
        view_func=CollaborationView.workspace,
        methods=["GET"],
        endpoint="workspace_channel",
    )
    collaboration_bp.add_url_rule("/collaboration/dialog", view_func=CollaborationView.dialog, methods=["GET"], endpoint="dialog")
    collaboration_bp.add_url_rule(
        "/collaboration/dialog",
        view_func=CollaborationView.submit_dialog,
        methods=["POST"],
        endpoint="submit_dialog",
    )
    collaboration_bp.add_url_rule("/collaboration/join", view_func=CollaborationView.join, methods=["GET"], endpoint="join")
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>/stories/<string:snapshot_id>/update",
        view_func=CollaborationView.update_story,
        methods=["POST"],
        endpoint="update_story",
    )
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>/stories/<string:snapshot_id>/news-items/<string:news_item_id>/move",
        view_func=CollaborationView.move_news_item,
        methods=["POST"],
        endpoint="move_news_item",
    )
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>/finalize",
        view_func=CollaborationView.finalize,
        methods=["POST"],
        endpoint="finalize",
    )
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>/report-dialog",
        view_func=CollaborationView.report_dialog,
        methods=["POST"],
        endpoint="report_dialog",
    )
    collaboration_bp.add_url_rule(
        "/collaboration/report",
        view_func=CollaborationView.submit_report_dialog,
        methods=["POST"],
        endpoint="submit_report_dialog",
    )
    collaboration_bp.add_url_rule(
        "/collaboration/<string:channel_id>/close",
        view_func=CollaborationView.close,
        methods=["POST"],
        endpoint="close",
    )

    app.register_blueprint(collaboration_bp)
