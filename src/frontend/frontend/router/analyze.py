from flask import Blueprint, Flask

from frontend.views.report_views import ReportItemView


def init(app: Flask):
    analyze_bp = Blueprint("analyze", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    analyze_bp.add_url_rule("/analyze", view_func=ReportItemView.as_view("analyze"))
    analyze_bp.add_url_rule("/report/<string:report_id>", view_func=ReportItemView.as_view("report"))
    analyze_bp.add_url_rule("/report/<string:report_id>/cti", view_func=ReportItemView.cti_dialog, endpoint="report_cti")
    analyze_bp.add_url_rule("/report/<string:report_id>/versions", view_func=ReportItemView.versions_view, endpoint="report_versions")
    analyze_bp.add_url_rule(
        "/report/<string:report_id>/diff/<int:from_rev>..<int:to_rev>", view_func=ReportItemView.diff_view, endpoint="report_diff"
    )
    analyze_bp.add_url_rule(
        "/analyze/clone/<string:report_id>", view_func=ReportItemView.clone_report, methods=["POST"], endpoint="clone_report"
    )
    analyze_bp.add_url_rule(
        "/report/<string:report_id>/bots",
        view_func=ReportItemView.trigger_bot_action,
        methods=["POST"],
        endpoint="report_trigger_bot",
    )
    analyze_bp.add_url_rule(
        "/reports/bots",
        view_func=ReportItemView.trigger_bot_action,
        methods=["POST"],
        endpoint="reports_trigger_bot",
    )

    app.register_blueprint(analyze_bp)
