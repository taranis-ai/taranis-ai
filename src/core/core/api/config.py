import io

from flask import request, send_file
from flask_restful import Resource

from core.managers import (
    auth_manager,
    sse_manager,
    remote_manager,
    presenters_manager,
    publishers_manager,
    bots_manager,
    external_auth_manager,
    collectors_manager,
)
from core.managers.log_manager import logger
from core.managers.auth_manager import auth_required, get_user_from_jwt
from core.model import (
    acl_entry,
    attribute,
    bot,
    bots_node,
    collector,
    collectors_node,
    parameter,
    presenter,
    presenters_node,
    product_type,
    publisher,
    publisher_preset,
    publishers_node,
    remote,
    organization,
    osint_source,
    report_item_type,
    role,
    user,
    word_list,
)
from core.model.news_item import NewsItemAggregate
from core.model.permission import Permission
from shared.schema.role import PermissionSchema


class DictionariesReload(Resource):
    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def get(self, dictionary_type):
        attribute.Attribute.load_dictionaries(dictionary_type)
        return "success", 200


class Attributes(Resource):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS", "ANALYZE_ACCESS"])
    def get(self):
        search = request.args.get(key="search", default=None)
        return attribute.Attribute.get_all_json(search)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self):
        attribute.Attribute.add_attribute(request.json)


class Attribute(Resource):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS", "ANALYZE_ACCESS"])
    def get(self, attribute_id):
        return attribute.Attribute.find_by_id(attribute_id)

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id):
        attribute.Attribute.update(attribute_id, request.json)

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id):
        return attribute.Attribute.delete_attribute(attribute_id)


class AttributeEnums(Resource):
    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self, attribute_id):
        search = request.args.get(key="search", default=None)
        offset = request.args.get(key="offset", default=0)
        limit = request.args.get(key="limit", default=10)
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def post(self, attribute_id):
        attribute.AttributeEnum.add(attribute_id, request.json)


class AttributeEnum(Resource):
    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id, enum_id):
        attribute.AttributeEnum.update(enum_id, request.json)

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def delete(self, attribute_id, enum_id):
        return attribute.AttributeEnum.delete(enum_id)


class ReportItemTypesConfig(Resource):
    @auth_required("CONFIG_REPORT_TYPE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return report_item_type.ReportItemType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self):
        report_item_type.ReportItemType.add_report_item_type(request.json)


class ReportItemType(Resource):
    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id):
        report_item_type.ReportItemType.update(type_id, request.json)

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id):
        return report_item_type.ReportItemType.delete_report_item_type(type_id)


class ProductTypes(Resource):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        product_type.ProductType.add_new(request.json)


class ProductType(Resource):
    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id):
        product_type.ProductType.update(type_id, request.json)

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id):
        return product_type.ProductType.delete(type_id)


class Permissions(Resource):
    @auth_required("CONFIG_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return Permission.get_all_json(search)


class ExternalPermissions(Resource):
    @auth_required("MY_ASSETS_CONFIG")
    def get(self):
        permissions = auth_manager.get_external_permissions()
        permissions_schema = PermissionSchema(many=True)
        return {
            "total_count": len(permissions),
            "items": permissions_schema.dump(permissions),
        }


class Roles(Resource):
    @auth_required("CONFIG_ROLE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return role.Role.get_all_json(search)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        role.Role.add_new(request.json)


class Role(Resource):
    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id):
        role.Role.update(role_id, request.json)

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id):
        return role.Role.delete(role_id)


class ACLEntries(Resource):
    @auth_required("CONFIG_ACL_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return acl_entry.ACLEntry.get_all_json(search)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self):
        acl_entry.ACLEntry.add_new(request.json)


class ACLEntry(Resource):
    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id):
        acl_entry.ACLEntry.update(acl_id, request.json)

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id):
        return acl_entry.ACLEntry.delete(acl_id)


class Organizations(Resource):
    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return organization.Organization.get_all_json(search)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self):
        organization.Organization.add_new(request.json)


class Organization(Resource):
    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id):
        organization.Organization.update(organization_id, request.json)

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id):
        return organization.Organization.delete(organization_id)


class Users(Resource):
    @auth_required("CONFIG_USER_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return user.User.get_all_json(search)

    @auth_required("CONFIG_USER_CREATE")
    def post(self):
        try:
            external_auth_manager.create_user(request.json)
        except Exception as ex:
            logger.log_debug(ex)
            logger.store_data_error_activity(get_user_from_jwt(), "Could not create user in external auth system")
            return "", 400

        user.User.add_new(request.json)


class User(Resource):
    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id):
        try:
            if external_auth_manager.keycloak_user_management_enabled():
                original_user = user.User.find_by_id(user_id)
                original_username = original_user.username
                external_auth_manager.update_user(request.json, original_username)
        except Exception:
            logger.exception()
            logger.store_data_error_activity(get_user_from_jwt(), "Could not update user in external auth system")
            return "", 400

        user.User.update(user_id, request.json)

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id):
        original_user = user.User.find_by_id(user_id)
        original_username = original_user.username

        user.User.delete(user_id)

        try:
            external_auth_manager.delete_user(original_username)
        except Exception as ex:
            logger.log_debug(ex)
            logger.store_data_error_activity(get_user_from_jwt(), "Could not delete user in external auth system")
            return "", 400


class ExternalUsers(Resource):
    @auth_required("CONFIG_USER_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        permissions = auth_manager.get_external_permissions_ids()
        user.User.add_new_external(auth_manager.get_user_from_jwt(), permissions, request.json)


class ExternalUser(Resource):
    @auth_required("CONFIG_USER_ACCESS")
    def put(self, user_id):
        permissions = auth_manager.get_external_permissions_ids()
        user.User.update_external(auth_manager.get_user_from_jwt(), permissions, user_id, request.json)

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, user_id):
        return user.User.delete_external(auth_manager.get_user_from_jwt(), user_id)


class WordLists(Resource):
    @auth_required("CONFIG_WORD_LIST_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return word_list.WordList.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self):
        word_list.WordList.add_new(request.json)


class WordList(Resource):
    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id):
        return word_list.WordList.delete(word_list_id)

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        word_list.WordList.update(word_list_id, request.json)


class Collectors(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return collector.Collector.get_all_json(search)


class Bots(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return bot.Bot.get_all_json(search)

    def put(self, bot_id):
        return bot.Bot.update_bot_parameters(bot_id, request.json)


class Parameters(Resource):
    def get(self):
        return parameter.Parameter.get_all_json()


class CollectorsNodes(Resource):
    @auth_required("CONFIG_COLLECTORS_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return collectors_node.CollectorsNode.get_all_json(search)

    @auth_required("CONFIG_COLLECTORS_NODE_CREATE")
    def post(self):
        return collectors_manager.add_collectors_node(request.json)

    @auth_required("CONFIG_COLLECTORS_NODE_UPDATE")
    def put(self, node_id):
        collectors_manager.update_collectors_node(node_id, request.json)

    @auth_required("CONFIG_COLLECTORS_NODE_DELETE")
    def delete(self, node_id):
        collectors_node.CollectorsNode.delete(node_id)


class RefreshWorkers(Resource):
    @auth_required("CONFIG_COLLECTORS_NODE_UPDATE")
    def post(self):
        collectors_manager.refresh_collectors()
        bots_manager.refresh_bots()


class OSINTSources(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return osint_source.OSINTSource.get_all_json(search)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        collectors_manager.add_osint_source(request.json)


class OSINTSource(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self, source_id):
        return osint_source.OSINTSource.get_by_id(source_id)

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id):
        updated_osint_source, default_group = collectors_manager.update_osint_source(source_id, request.json)
        if default_group is not None:
            NewsItemAggregate.reassign_to_new_groups(updated_osint_source.id, default_group.id)

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id):
        collectors_manager.delete_osint_source(source_id)


class OSINTSourceRefresh(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def put(self, source_id):
        result = collectors_manager.refresh_osint_source(source_id)
        return result


class OSINTSourcesExport(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        ids = request.args.getlist(key="ids")
        data = collectors_manager.export_osint_sources(ids)
        if data is None:
            return "", 400
        return send_file(
            io.BytesIO(data),
            download_name="osint_sources_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class OSINTSourcesImport(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        if file := request.files.get("file"):
            collectors_manager.import_osint_sources(file)


class OSINTSourceGroups(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        osint_source.OSINTSourceGroup.add(request.json)


class OSINTSourceGroup(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id):
        sources_in_default_group, message, code = osint_source.OSINTSourceGroup.update(group_id, request.json)
        if sources_in_default_group is not None:
            default_group = osint_source.OSINTSourceGroup.get_default()
            for source in sources_in_default_group:
                NewsItemAggregate.reassign_to_new_groups(source.id, default_group.id)

        return message, code

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id):
        return osint_source.OSINTSourceGroup.delete(group_id)


class RemoteAccesses(Resource):
    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return remote.RemoteAccess.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self):
        remote.RemoteAccess.add(request.json)


class RemoteAccess(Resource):
    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_access_id):
        event_id, disconnect = remote.RemoteAccess.update(remote_access_id, request.json)
        if disconnect:
            sse_manager.remote_access_disconnect([event_id])

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_access_id):
        return remote.RemoteAccess.delete(remote_access_id)


class RemoteNodes(Resource):
    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return remote.RemoteNode.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self):
        remote.RemoteNode.add(request.json)


class RemoteNode(Resource):
    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_node_id):
        if remote.RemoteNode.update(id, request.json) is False:
            remote_manager.disconnect_from_node(remote_node_id)

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_node_id):
        remote_manager.disconnect_from_node(remote_node_id)
        return remote.RemoteNode.delete(id)


class RemoteNodeConnect(Resource):
    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self, remote_node_id):
        return remote_manager.connect_to_node(remote_node_id)


class Presenters(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return presenter.Presenter.get_all_json(search)


class Publishers(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher.Publisher.get_all_json(search)


class PresentersNodes(Resource):
    @auth_required("CONFIG_PRESENTERS_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return presenters_node.PresentersNode.get_all_json(search)

    @auth_required("CONFIG_PRESENTERS_NODE_CREATE")
    def post(self):
        return "", presenters_manager.add_presenters_node(request.json)

    @auth_required("CONFIG_PRESENTERS_NODE_UPDATE")
    def put(self, node_id):
        presenters_manager.update_presenters_node(node_id, request.json)

    @auth_required("CONFIG_PRESENTERS_NODE_DELETE")
    def delete(self, node_id):
        return presenters_node.PresentersNode.delete(node_id)


class PublisherNodes(Resource):
    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return publishers_node.PublishersNode.get_all_json(search)

    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self):
        return "", publishers_manager.add_publishers_node(request.json)

    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, node_id):
        publishers_manager.update_publishers_node(node_id, request.json)

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, node_id):
        return publishers_node.PublishersNode.delete(node_id)


class PublisherPresets(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        publishers_manager.add_publisher_preset(request.json)


class PublisherPreset(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, preset_id):
        publisher_preset.PublisherPreset.update(preset_id, request.json)

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, preset_id):
        return publisher_preset.PublisherPreset.delete(preset_id)


class Nodes(Resource):
    @auth_required("CONFIG_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        publishers_nodes = publishers_node.PublishersNode.get_all_json(search)
        bots_nodes = bots_node.BotsNode.get_all_json(search)
        collectors_nodes = collectors_node.CollectorsNode.get_all_json(search)
        presenters_nodes = presenters_node.PresentersNode.get_all_json(search)
        total_count = (
            publishers_nodes["total_count"] + bots_nodes["total_count"] + collectors_nodes["total_count"] + presenters_nodes["total_count"]
        )
        items = publishers_nodes["items"] + bots_nodes["items"] + collectors_nodes["items"] + presenters_nodes["items"]
        return {"total_count": total_count, "items": items}


class BotNodes(Resource):
    @auth_required("CONFIG_BOTS_NODE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return bots_node.BotsNode.get_all_json(search)

    @auth_required("CONFIG_BOTS_NODE_CREATE")
    def post(self):
        return bots_manager.add_bots_node(request.json)

    @auth_required("CONFIG_BOTS_NODE_UPDATE")
    def put(self, node_id):
        bots_manager.update_bots_node(node_id, request.json)

    @auth_required("CONFIG_BOTS_NODE_DELETE")
    def delete(self, node_id):
        return bots_node.BotsNode.delete(node_id)


def initialize(api):
    api.add_resource(
        DictionariesReload,
        "/api/v1/config/reload-enum-dictionaries/<string:dictionary_type>",
    )
    api.add_resource(Attributes, "/api/v1/config/attributes")
    api.add_resource(Attribute, "/api/v1/config/attributes/<int:attribute_id>")
    api.add_resource(AttributeEnums, "/api/v1/config/attributes/<int:attribute_id>/enums")
    api.add_resource(
        AttributeEnum,
        "/api/v1/config/attributes/<int:attribute_id>/enums/<int:enum_id>",
    )

    api.add_resource(ReportItemTypesConfig, "/api/v1/config/report-item-types")
    api.add_resource(ReportItemType, "/api/v1/config/report-item-types/<int:type_id>")

    api.add_resource(ProductTypes, "/api/v1/config/product-types")
    api.add_resource(ProductType, "/api/v1/config/product-types/<int:type_id>")

    api.add_resource(Permissions, "/api/v1/config/permissions")
    api.add_resource(ExternalPermissions, "/api/v1/config/external-permissions")
    api.add_resource(Roles, "/api/v1/config/roles")
    api.add_resource(Role, "/api/v1/config/roles/<int:role_id>")
    api.add_resource(ACLEntries, "/api/v1/config/acls")
    api.add_resource(ACLEntry, "/api/v1/config/acls/<int:acl_id>")

    api.add_resource(Organizations, "/api/v1/config/organizations")
    api.add_resource(Organization, "/api/v1/config/organizations/<int:organization_id>")

    api.add_resource(Users, "/api/v1/config/users")
    api.add_resource(User, "/api/v1/config/users/<int:user_id>")

    api.add_resource(ExternalUsers, "/api/v1/config/external-users")
    api.add_resource(ExternalUser, "/api/v1/config/external-users/<int:user_id>")

    api.add_resource(WordLists, "/api/v1/config/word-lists")
    api.add_resource(WordList, "/api/v1/config/word-lists/<int:word_list_id>")

    api.add_resource(CollectorsNodes, "/api/v1/config/collectors-nodes", "/api/v1/config/collectors-nodes/<string:node_id>")
    api.add_resource(RefreshWorkers, "/api/v1/config/workers/refresh")
    api.add_resource(Collectors, "/api/v1/config/collectors", "/api/v1/config/collectors/<string:collector_type>")
    api.add_resource(Bots, "/api/v1/config/bots", "/api/v1/config/bots/<string:bot_id>")
    api.add_resource(Parameters, "/api/v1/config/parameters")

    api.add_resource(OSINTSources, "/api/v1/config/osint-sources")
    api.add_resource(OSINTSource, "/api/v1/config/osint-sources/<string:source_id>")
    api.add_resource(OSINTSourceRefresh, "/api/v1/config/osint-sources/<string:source_id>/refresh")
    api.add_resource(OSINTSourcesExport, "/api/v1/config/export-osint-sources")
    api.add_resource(OSINTSourcesImport, "/api/v1/config/import-osint-sources")
    api.add_resource(OSINTSourceGroups, "/api/v1/config/osint-source-groups")
    api.add_resource(OSINTSourceGroup, "/api/v1/config/osint-source-groups/<string:group_id>")

    api.add_resource(RemoteAccesses, "/api/v1/config/remote-accesses")
    api.add_resource(RemoteAccess, "/api/v1/config/remote-accesses/<int:remote_access_id>")

    api.add_resource(RemoteNodes, "/api/v1/config/remote-nodes")
    api.add_resource(RemoteNode, "/api/v1/config/remote-nodes/<int:remote_node_id>")
    api.add_resource(RemoteNodeConnect, "/api/v1/config/remote-nodes/<int:remote_node_id>/connect")

    api.add_resource(Presenters, "/api/v1/config/presenters")
    api.add_resource(Publishers, "/api/v1/config/publishers")
    api.add_resource(PresentersNodes, "/api/v1/config/presenters-nodes", "/api/v1/config/presenters-nodes/<string:node_id>")
    api.add_resource(PublisherNodes, "/api/v1/config/publishers-nodes", "/api/v1/config/publishers-nodes/<string:node_id>")
    api.add_resource(PublisherPresets, "/api/v1/config/publishers-presets")
    api.add_resource(PublisherPreset, "/api/v1/config/publishers-presets/<string:preset_id>")

    api.add_resource(BotNodes, "/api/v1/config/bots-nodes", "/api/v1/config/bots-nodes/<string:node_id>")

    api.add_resource(Nodes, "/api/v1/config/nodes", "/api/v1/config/nodes/<string:node_id>")
