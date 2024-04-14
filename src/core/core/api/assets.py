from flask import request, Flask
from flask.views import MethodView

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import asset, attribute
from core.model.attribute import AttributeType


class AssetGroups(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, group_id=None):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "User not found"}, 404
        if group_id:
            return asset.AssetGroup.get_json(user.organization, group_id)

        search = request.args.get("search", None)
        return asset.AssetGroup.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("ASSETS_CONFIG")
    def post(self):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "User not found"}, 404
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        data["organization"] = user.organization
        asset_result = asset.AssetGroup.add(data)
        return {"message": "Asset Group added", "id": asset_result.id}, 201

    @auth_required("ASSETS_CONFIG")
    def delete(self, group_id):
        if user := auth_manager.get_user_from_jwt():
            return asset.AssetGroup.delete(user.organization, group_id)
        return {"error": "User not found"}, 404

    @auth_required("ASSETS_CONFIG")
    def put(self, group_id):
        if user := auth_manager.get_user_from_jwt():
            return asset.AssetGroup.update(user.organization, group_id, request.json)
        return {"error": "User not found"}, 404


class Assets(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id=None):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "User not found"}, 404

        if asset_id:
            return asset.Asset.get_json(user.organization, asset_id)
        filter_keys = ["search" "vulnerable", "group", "sort"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        return asset.Asset.get_all_json(user.organization, filter_args)

    @auth_required("ASSETS_CREATE")
    def post(self):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "User not found"}, 404
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        return asset.Asset.add(user.organization, data)

    @auth_required("ASSETS_CREATE")
    def put(self, asset_id):
        if user := auth_manager.get_user_from_jwt():
            return asset.Asset.update(user.organization, asset_id, request.json)
        return {"error": "User not found"}, 404

    @auth_required("ASSETS_CREATE")
    def delete(self, asset_id):
        if user := auth_manager.get_user_from_jwt():
            return asset.Asset.delete(user.organization, asset_id)
        return {"error": "User not found"}, 404


class AssetVulnerability(MethodView):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id, vulnerability_id):
        data = request.json
        if not data or "solved" not in data:
            return {"message": "Missing solved field"}, 400
        if user := auth_manager.get_user_from_jwt():
            return asset.Asset.solve_vulnerability(user.organization, asset_id, vulnerability_id, data["solved"])
        return {"error": "User not found"}, 404


class GetAttributeCPE(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        search = request.args.get("search")
        limit = min(int(request.args.get("limit", 20)), 200)
        offset = int(request.args.get("offset", 0))

        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(app: Flask):
    base_route = "/api"
    app.add_url_rule(f"{base_route}/assets", view_func=Assets.as_view("assets"))
    app.add_url_rule(f"{base_route}/assets/<int:asset_id>", view_func=Assets.as_view("asset"))
    app.add_url_rule(
        f"{base_route}/assets/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
        view_func=AssetVulnerability.as_view("asset_vulnerability"),
    )
    app.add_url_rule(f"{base_route}/asset-groups", view_func=AssetGroups.as_view("asset_groups"))
    app.add_url_rule(f"{base_route}/asset-groups/<string:group_id>", view_func=AssetGroups.as_view("asset_group"))
    app.add_url_rule(f"{base_route}/asset-attributes/cpe", view_func=GetAttributeCPE.as_view("cpe"))
    app.add_url_rule(f"{base_route}/asset-attributes/cpe/enums", view_func=AttributeCPEEnums.as_view("cpe_enums"))
