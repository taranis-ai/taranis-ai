from flask import Blueprint, Flask

from frontend.views.asset_views import AssetView


def init(app: Flask):
    asset_bp = Blueprint("assets", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    asset_bp.add_url_rule("/assets", view_func=AssetView.as_view("assets"))
    asset_bp.add_url_rule("/assets/cti", view_func=AssetView.all_cti_dialog, endpoint="assets_cti")
    asset_bp.add_url_rule("/assets/<string:asset_id>", view_func=AssetView.as_view("asset"))
    asset_bp.add_url_rule("/assets/<string:asset_id>/cti", view_func=AssetView.cti_dialog, endpoint="asset_cti")

    app.register_blueprint(asset_bp)
