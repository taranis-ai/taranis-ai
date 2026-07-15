from typing import Any

from flask import render_template
from models.asset import Asset
from models.cti import CTIResponse

from frontend.auth import auth_required
from frontend.core_api import CoreApi
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
    observable_types = ["cve", "email", "ip", "domain", "url", "hash"]

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        observables = form_data.get("asset_observables", [])
        if isinstance(observables, dict):
            observables = list(observables.values())
        if not isinstance(observables, list):
            observables = []
        form_data["asset_observables"] = [
            {"ioc_type": str(item.get("ioc_type") or "").strip(), "value": str(item.get("value") or "").strip()}
            for item in observables
            if isinstance(item, dict) and (str(item.get("ioc_type") or "").strip() or str(item.get("value") or "").strip())
        ]
        return form_data

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        asset = base_context.get("asset")
        observables = getattr(asset, "asset_observables", []) if asset else []
        base_context["asset_observables"] = [
            observable.model_dump(mode="json") if hasattr(observable, "model_dump") else observable for observable in observables
        ]
        base_context["asset_observable_types"] = cls.observable_types
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @staticmethod
    @auth_required()
    def cti_dialog(asset_id: str) -> tuple[str, int]:
        payload = CoreApi().api_get(f"/assets/{asset_id}/cti") or {"item_type": "asset", "item_id": asset_id, "iocs": []}
        return render_template("shared/cti_dialog.html", cti=CTIResponse.model_validate(payload)), 200

    @staticmethod
    @auth_required()
    def all_cti_dialog() -> tuple[str, int]:
        payload = CoreApi().api_get("/assets/cti") or {"item_type": "asset", "item_id": "all", "iocs": []}
        return render_template("shared/cti_dialog.html", cti=CTIResponse.model_validate(payload)), 200
