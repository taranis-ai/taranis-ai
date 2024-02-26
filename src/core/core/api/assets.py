from flask import request
from flask_restx import Resource, Namespace, Api

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import asset, attribute
from core.model.attribute import AttributeType


class AssetGroups(Resource):
    @auth_required("ASSETS_ACCESS")
    def get(self):
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


class AssetGroup(Resource):
    @auth_required("ASSETS_CONFIG")
    def put(self, group_id):
        asset.AssetGroup.update(auth_manager.get_user_from_jwt(), group_id, request.json)

    @auth_required("ASSETS_CONFIG")
    def delete(self, group_id):
        return asset.AssetGroup.delete(auth_manager.get_user_from_jwt(), group_id)


class Assets(Resource):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        filter_keys = ["search" "vulnerable", "group", "sort"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        return asset.Asset.get_all_json(auth_manager.get_user_from_jwt(), filter_args)

    @auth_required("ASSETS_CREATE")
    def post(self):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "User not found"}, 404
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        return asset.Asset.add(user, data)


class Asset(Resource):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id):
        if user := auth_manager.get_user_from_jwt():
            return asset.Asset.get_json(user.organization, asset_id)
        return {"message": "User not found"}, 404

    @auth_required("ASSETS_CREATE")
    def put(self, asset_id):
        return asset.Asset.update(auth_manager.get_user_from_jwt(), asset_id, request.json)

    @auth_required("ASSETS_CREATE")
    def delete(self, asset_id):
        return asset.Asset.delete(auth_manager.get_user_from_jwt(), asset_id)


class AssetVulnerability(Resource):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id, vulnerability_id):
        data = request.json
        if not data or "solved" not in data:
            return {"message": "Missing solved field"}, 400
        return asset.Asset.solve_vulnerability(
            auth_manager.get_user_from_jwt(),
            asset_id,
            vulnerability_id,
            data["solved"],
        )


class GetAttributeCPE(Resource):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(Resource):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        search = request.args.get("search")
        limit = min(int(request.args.get("limit", 20)), 200)
        offset = int(request.args.get("offset", 0))

        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(api: Api):
    asset_namespace = Namespace("Assets", description="Assets related operations")
    asset_groups_namespace = Namespace("AssetGroups", description="Assets related operations")
    asset_attributes_namespace = Namespace("AssetAttributes", description="Assets related operations")
    asset_groups_namespace.add_resource(AssetGroups, "/", "")
    asset_groups_namespace.add_resource(AssetGroup, "/<string:group_id>")

    asset_namespace.add_resource(Assets, "/", "")
    asset_namespace.add_resource(Asset, "/<int:asset_id>")

    asset_namespace.add_resource(
        AssetVulnerability,
        "/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
    )

    asset_attributes_namespace.add_resource(GetAttributeCPE, "/cpe")
    asset_attributes_namespace.add_resource(AttributeCPEEnums, "/cpe/enums")
    api.add_namespace(asset_namespace, path="/assets")
    api.add_namespace(asset_groups_namespace, path="/asset-groups")
    api.add_namespace(asset_attributes_namespace, path="/asset-attributes")
