from typing import Any

from models.asset import Asset
from frontend.views.base_view import BaseView


class AssetView(BaseView):
    model = Asset
    icon = "document-chart-bar"
    htmx_list_template = "assets/assets_table.html"
    htmx_update_template = "assets/asset.html"
    edit_template = "assets/asset_view.html"
    default_template = "assets/index.html"

    base_route = "assets.assets"
    edit_route = "assets.asset"
    _read_only = True
    _show_sidebar = False

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]
