from flask import request
from flask_restful import Resource

from core.managers import auth_manager
from core.managers.auth_manager import auth_required
from core.model import asset, notification_template, attribute
from shared.schema.attribute import AttributeType


class AssetGroups(Resource):
    @auth_required("MY_ASSETS_ACCESS")
    def get(self):
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return asset.AssetGroup.get_all_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        return "", asset.AssetGroup.add(auth_manager.get_user_from_jwt(), request.json)


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
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
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
    def get(self, group_id):
        search = None
        sort = None
        vulnerable = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        if "sort" in request.args and request.args["sort"]:
            sort = request.args["sort"]
        if "vulnerable" in request.args and request.args["vulnerable"]:
            vulnerable = request.args["vulnerable"]
        return asset.Asset.get_all_json(auth_manager.get_user_from_jwt(), group_id, search, sort, vulnerable)

    @auth_required("MY_ASSETS_CREATE")
    def post(self, group_id):
        return "", asset.Asset.add(auth_manager.get_user_from_jwt(), group_id, request.json)


class Asset(Resource):
    @auth_required("MY_ASSETS_CREATE")
    def put(self, group_id, asset_id):
        asset.Asset.update(auth_manager.get_user_from_jwt(), group_id, asset_id, request.json)

    @auth_required("MY_ASSETS_CREATE")
    def delete(self, group_id, asset_id):
        return asset.Asset.delete(auth_manager.get_user_from_jwt(), group_id, asset_id)


class AssetVulnerability(Resource):
    @auth_required("MY_ASSETS_CREATE")
    def put(self, group_id, asset_id, vulnerability_id):
        return asset.Asset.solve_vulnerability(
            auth_manager.get_user_from_jwt(),
            group_id,
            asset_id,
            vulnerability_id,
            request.json["solved"],
        )


class GetAttributeCPE(Resource):
    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(Resource):
    @auth_required("MY_ASSETS_CREATE")
    def get(self):
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        search = None
        offset = 0
        limit = 10
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        if "offset" in request.args and request.args["offset"]:
            offset = request.args["offset"]
        if "limit" in request.args and request.args["limit"]:
            limit = request.args["limit"]
        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(api):
    api.add_resource(AssetGroups, "/api/v1/my-assets/asset-groups")
    api.add_resource(AssetGroup, "/api/v1/my-assets/asset-groups/<string:group_id>")

    api.add_resource(NotificationTemplates, "/api/v1/my-assets/asset-notification-templates")
    api.add_resource(
        NotificationTemplate,
        "/api/v1/my-assets/asset-notification-templates/<int:template_id>",
    )

    api.add_resource(Assets, "/api/v1/my-assets/asset-groups/<string:group_id>/assets")
    api.add_resource(Asset, "/api/v1/my-assets/asset-groups/<string:group_id>/assets/<int:asset_id>")

    api.add_resource(
        AssetVulnerability,
        "/api/v1/my-assets/asset-groups/<string:group_id>/assets/<int:asset_id>/vulnerabilities/<int:vulnerability_id>",
    )

    api.add_resource(GetAttributeCPE, "/api/v1/my-assets/attributes/cpe")
    api.add_resource(AttributeCPEEnums, "/api/v1/my-assets/attributes/cpe/enums")
