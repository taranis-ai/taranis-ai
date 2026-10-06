from flask import Blueprint, Flask

from frontend.views.asset_intelligence_views import asset_intelligence, asset_triggers
from frontend.views.asset_sbom_views import asset_inventory, preview_sbom, upload_sbom
from frontend.views.asset_views import AssetView


def init(app: Flask):
    asset_bp = Blueprint("assets", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}")

    asset_bp.add_url_rule("/assets", view_func=AssetView.as_view("assets"))
    asset_bp.add_url_rule("/assets/cti", view_func=AssetView.all_cti_dialog, endpoint="assets_cti")
    asset_bp.add_url_rule("/assets/<string:asset_id>", view_func=AssetView.as_view("asset"))
    asset_bp.add_url_rule("/assets/<string:asset_id>/cti", view_func=AssetView.cti_dialog, endpoint="asset_cti")

    asset_bp.add_url_rule("/assets/import-sbom", view_func=upload_sbom, endpoint="sbom_upload", methods=["GET", "POST"])
    asset_bp.add_url_rule("/assets/sbom-imports/<string:import_id>", view_func=preview_sbom, endpoint="sbom_preview", methods=["GET", "POST"])
    asset_bp.add_url_rule("/assets/<string:asset_id>/sbom", view_func=asset_inventory, endpoint="asset_sbom")
    asset_bp.add_url_rule("/assets/<string:asset_id>/triggers", view_func=asset_triggers, endpoint="asset_triggers", methods=["GET", "POST"])
    asset_bp.add_url_rule(
        "/assets/<string:asset_id>/intelligence", view_func=asset_intelligence, endpoint="asset_intelligence", methods=["GET", "POST"]
    )

    app.register_blueprint(asset_bp)
