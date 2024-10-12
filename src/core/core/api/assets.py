from flask import request, Flask
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.managers.auth_manager import auth_required
from core.model import asset
from core.managers.decorators import extract_args
from core.config import Config


class AssetGroups(MethodView):
    @auth_required("ASSETS_ACCESS")
    @extract_args("search")
    def get(self, group_id=None, filter_args=None):
        if group_id:
            return asset.AssetGroup.get_for_api(group_id, current_user.organization)

        filter_args = filter_args or {}
        filter_args["organization"] = current_user.organization
        return asset.AssetGroup.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("ASSETS_CONFIG")
    def post(self):
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        data["organization"] = current_user.organization
        asset_result = asset.AssetGroup.add(data)
        return {"message": "Asset Group added", "id": asset_result.id}, 201

    @auth_required("ASSETS_CONFIG")
    def delete(self, group_id):
        return asset.AssetGroup.delete(current_user.organization, group_id)

    @auth_required("ASSETS_CONFIG")
    def put(self, group_id):
        return asset.AssetGroup.update(current_user.organization, group_id, request.json)


class Assets(MethodView):
    @auth_required("ASSETS_ACCESS")
    @extract_args("search", "vulnerable", "group", "sort")
    def get(self, asset_id=None, filter_args=None):
        if asset_id:
            return asset.Asset.get_for_api(asset_id, current_user.organization)
        filter_args = filter_args or {}
        filter_args["organization"] = current_user.organization
        return asset.Asset.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("ASSETS_CREATE")
    def post(self):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        return asset.Asset.add(current_user.organization, data)

    @auth_required("ASSETS_CREATE")
    def put(self, asset_id):
        return asset.Asset.update(current_user.organization, asset_id, request.json)

    @auth_required("ASSETS_CREATE")
    def delete(self, asset_id):
        return asset.Asset.delete(current_user.organization, asset_id)


class AssetVulnerability(MethodView):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id, vulnerability_id):
        data = request.json
        if not data or "solved" not in data:
            return {"message": "Missing solved field"}, 400
        return asset.Asset.solve_vulnerability(current_user.organization, asset_id, vulnerability_id, data["solved"])


def initialize(app: Flask):
    base_route = f"{Config.APPLICATION_ROOT}api"
    app.add_url_rule(f"{base_route}/assets", view_func=Assets.as_view("assets"))
    app.add_url_rule(f"{base_route}/assets/<int:asset_id>", view_func=Assets.as_view("asset"))
    app.add_url_rule(
        f"{base_route}/assets/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
        view_func=AssetVulnerability.as_view("asset_vulnerability"),
    )
    app.add_url_rule(f"{base_route}/asset-groups", view_func=AssetGroups.as_view("asset_groups"))
    app.add_url_rule(f"{base_route}/asset-groups/<string:group_id>", view_func=AssetGroups.as_view("asset_group"))
