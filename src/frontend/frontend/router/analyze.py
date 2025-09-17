from flask import Flask, Blueprint

from frontend.views.report_views import ReportItemView


def init(app: Flask):
    analyze_bp = Blueprint("analyze", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    analyze_bp.add_url_rule("/analyze", view_func=ReportItemView.as_view("analyze"))
    analyze_bp.add_url_rule("/analyze/<string:report_id>", view_func=ReportItemView.as_view("report"))
    analyze_bp.add_url_rule("/report/<string:report_id>", view_func=ReportItemView.as_view("report_"))

    app.register_blueprint(analyze_bp)
