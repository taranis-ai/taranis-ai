from flask import request
from flask_restx import Resource, Namespace

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import asset, notification_template, attribute
from core.model.attribute import AttributeType


class AssetGroups(Resource):
    @auth_required("MY_ASSETS_ACCESS")
    def get(self):
        search = request.args.get("search", None)
        return asset.AssetGroup.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        return asset.AssetGroup.add(auth_manager.get_user_from_jwt(), request.json)


class AssetGroup(Resource):
    @auth_required("MY_ASSETS_CONFIG")
    def put(self, group_id):
        asset.AssetGroup.update(auth_manager.get_user_from_jwt(), group_id, request.json)

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, group_id):
        return asset.AssetGroup.delete(auth_manager.get_user_from_jwt(), group_id)


class NotificationTemplates(Resource):
    @auth_required("MY_ASSETS_CONFIG")
    def get(self):
        search = request.args.get("search", None)
        return notification_template.NotificationTemplate.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        return "", notification_template.NotificationTemplate.add(auth_manager.get_user_from_jwt(), request.json)


class NotificationTemplate(Resource):
    @auth_required("MY_ASSETS_CONFIG")
    def put(self, template_id):
        notification_template.NotificationTemplate.update(auth_manager.get_user_from_jwt(), template_id, request.json)

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, template_id):
        return notification_template.NotificationTemplate.delete(auth_manager.get_user_from_jwt(), template_id)


class Assets(Resource):
    @auth_required("MY_ASSETS_ACCESS")
    def get(self):
        filter_keys = ["search" "vulnerable", "group", "sort"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        return asset.Asset.get_all_json(auth_manager.get_user_from_jwt(), filter_args)

    @auth_required("MY_ASSETS_CREATE")
    def post(self):
        return "", asset.Asset.add(auth_manager.get_user_from_jwt(), request.json)


class Asset(Resource):
    @auth_required("MY_ASSETS_ACCESS")
    def get(self, asset_id):
        return asset.Asset.get_json(auth_manager.get_user_from_jwt().organization, asset_id)

    @auth_required("MY_ASSETS_CREATE")
    def put(self, asset_id):
        return asset.Asset.update(auth_manager.get_user_from_jwt(), asset_id, request.json)

    @auth_required("MY_ASSETS_CREATE")
    def delete(self, asset_id):
        return asset.Asset.delete(auth_manager.get_user_from_jwt(), asset_id)


class AssetVulnerability(Resource):
    @auth_required("MY_ASSETS_CREATE")
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
    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(Resource):
    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        cpe = attribute.Attribute.filter_by_type(AttributeType.CPE)
        search = request.args.get("search")
        limit = min(int(request.args.get("limit", 20)), 200)
        offset = int(request.args.get("offset", 0))

        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(api):
    namespace = Namespace("Assets", description="Assets related operations", path="/api/v1")
    namespace.add_resource(AssetGroups, "/asset-groups")
    namespace.add_resource(AssetGroup, "/asset-groups/<string:group_id>")

    namespace.add_resource(NotificationTemplates, "/asset-notification-templates")
    namespace.add_resource(
        NotificationTemplate,
        "/asset-notification-templates/<int:template_id>",
    )

    namespace.add_resource(Assets, "/assets")
    namespace.add_resource(Asset, "/assets/<int:asset_id>")

    namespace.add_resource(
        AssetVulnerability,
        "/assets/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
    )

    namespace.add_resource(GetAttributeCPE, "/asset-attributes/cpe")
    namespace.add_resource(AttributeCPEEnums, "/asset-attributes/cpe/enums")
    api.add_namespace(namespace)
