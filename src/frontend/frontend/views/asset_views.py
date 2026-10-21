from typing import Any
from urllib.parse import urlencode

from flask import redirect, render_template, request, url_for
from flask_jwt_extended import current_user
from models.asset import Asset
from models.cti import CTIResponse
from requests import RequestException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.views.base_view import BaseView


def asset_display_name(asset_id: str | None) -> str | None:
    if not asset_id or "ASSETS_ACCESS" not in current_user.permissions:
        return None
    try:
        # Read current access rather than reuse a cached name after group changes.
        api = CoreApi()
        response = api.session.get(f"{api.api_url}/assets/{asset_id}", timeout=api.timeout)
        if response.ok:
            return Asset.model_validate(response.json()).name
    except RequestException, ValueError:
        logger.exception("Asset display name unavailable")
    return None


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
    observable_types = ("cve", "email", "ip", "domain", "url", "hash")

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        if "tags_text" in form_data:
            form_data["tags"] = str(form_data.pop("tags_text")).splitlines()
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
        if "asset" not in base_context:
            base_context["asset_tags"] = []
            try:
                api = CoreApi()
                response = api.session.get(f"{api.api_url}/assets/tags", timeout=api.timeout)
                if response.ok:
                    base_context["asset_tags"] = response.json()["tags"]
            except RequestException, ValueError:
                logger.exception("Asset tag choices unavailable")
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Tags", "field": "tags", "sortable": False, "renderer": lambda asset: ", ".join(asset.tags)},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @staticmethod
    @auth_required("ASSETS_ACCESS")
    def cti_dialog(asset_id: str) -> tuple[str, int]:
        return _render_asset_cti(asset_id)

    @staticmethod
    @auth_required("ASSETS_ACCESS")
    def all_cti_dialog() -> tuple[str, int]:
        return _render_asset_cti(None)

    @staticmethod
    @auth_required("ASSETS_CREATE")
    def cve_matching(asset_id: str, cve_id: str):
        overview = request.form.get("overview") == "true"
        try:
            response = CoreApi().api_put(f"/assets/{asset_id}/sbom/cves/{cve_id}", {"enabled": request.form.get("enabled") == "true"})
        except RequestException:
            logger.exception("CVE matching update failed")
            return _render_asset_cti(None if overview else asset_id, error="Unable to update CVE matching.", status=502)
        if not response.ok:
            return _render_asset_cti(None if overview else asset_id, error="Unable to update CVE matching.", status=response.status_code)
        target = url_for("assets.assets_cti") if overview else url_for("assets.asset_cti", asset_id=asset_id)
        query = urlencode({"page": request.form.get("page", "1"), "search": request.form.get("search", "")})
        return redirect(f"{target}?{query}", code=303)


def _render_asset_cti(asset_id: str | None, *, error=None, status=200) -> tuple[str, int]:
    filters = request.form if request.method == "POST" else request.args
    query = {"page": filters.get("page", "1"), "search": filters.get("search", "")}
    endpoint = f"/assets/{asset_id}/cti" if asset_id else "/assets/cti"
    api = CoreApi()
    cti = CTIResponse(item_type="asset", item_id=asset_id or "all")
    try:
        response = api.session.get(f"{api.api_url}{endpoint}", params=query, timeout=api.timeout)
        if response.ok:
            cti = CTIResponse.model_validate(response.json())
        else:
            error, status = "Unable to load asset findings and indicators.", response.status_code
    except RequestException, ValueError:
        logger.exception("Asset CTI read failed")
        error, status = "Unable to load asset findings and indicators.", 502
    cti_url = url_for("assets.asset_cti", asset_id=asset_id) if asset_id else url_for("assets.assets_cti")
    return render_template("shared/cti_dialog.html", cti=cti, cti_url=cti_url, error=error, asset_name=asset_display_name(asset_id)), status
