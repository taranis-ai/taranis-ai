import io

from flask import request, send_file, jsonify
from flask_restx import Resource, Namespace, Api

from core.managers import (
    auth_manager,
    presenters_manager,
    publishers_manager,
    bots_manager,
    queue_manager,
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
    queue,
)
from core.model.permission import Permission


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
        attribute_result = attribute.Attribute.add(request.json)
        return {"message": "Attribute added", "id": attribute_result.id}, 201


class Attribute(Resource):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS", "ANALYZE_ACCESS"])
    def get(self, attribute_id):
        result = attribute.Attribute.get(attribute_id)
        return result.to_json() if result else ("Attribute not found", 404)

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id):
        attribute.Attribute.update(attribute_id, request.json)

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id):
        return attribute.Attribute.delete(attribute_id)


class AttributeEnums(Resource):
    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self, attribute_id):
        search = request.args.get(key="search", default=None)
        offset = request.args.get(key="offset", default=0)
        limit = request.args.get(key="limit", default=10)
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def post(self, attribute_id):
        result = attribute.AttributeEnum.add(request.json)
        return {"message": "Attribute enum added", "id": result.id}, 201


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
        try:
            item = report_item_type.ReportItemType.add(request.json)
            return {"message": "Report item type added", "id": item.id}, 201
        except Exception:
            logger.exception("Failed to add report item type")
            return {"message": "Failed to add report item type"}, 500


class ReportItemType(Resource):
    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id):
        report_item_type.ReportItemType.update(type_id, request.json)

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id):
        return report_item_type.ReportItemType.delete(type_id)


class ProductTypes(Resource):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return jsonify(product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), False))

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        product = product_type.ProductType.add(request.json)
        return {"message": "Product type created", "id": product.id}, 201


class ProductType(Resource):
    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id):
        return product_type.ProductType.update(type_id, request.json)

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id):
        return product_type.ProductType.delete(type_id)


class Permissions(Resource):
    @auth_required("CONFIG_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return Permission.get_all_json(search)


class Roles(Resource):
    @auth_required("CONFIG_ROLE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return role.Role.get_all_json(search)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        new_role = role.Role.add(request.json)
        return {"message": "Role created", "id": new_role.id}, 201


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
        acl = acl_entry.ACLEntry.add(request.json)
        return {"message": "ACL created", "id": acl.id}, 201


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
        org = organization.Organization.add(request.json)
        return {"message": "Organization created", "id": org.id}, 201


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
            new_user = user.User.add(request.json)
            return {"message": "User created", "id": new_user.id}, 201
        except Exception:
            logger.exception()
            return "Could not create user", 400


class User(Resource):
    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id):
        try:
            return user.User.update(user_id, request.json), 200
        except Exception:
            logger.exception()
            logger.store_data_error_activity(get_user_from_jwt(), "Could not update user")
            return "Could not update user", 400

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id):
        try:
            original_user = user.User.find_by_id(user_id)
            return user.User.delete(user_id), 200

        except Exception as ex:
            logger.exception(ex)
            logger.store_data_error_activity(get_user_from_jwt(), "Could not delete user")
            return "Could not delete user", 400


class ExternalUsers(Resource):
    @auth_required("CONFIG_USER_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        return user.User.add_new_external(auth_manager.get_user_from_jwt(), request.json)


class ExternalUser(Resource):
    @auth_required("CONFIG_USER_ACCESS")
    def put(self, user_id):
        user.User.update_external(auth_manager.get_user_from_jwt(), user_id, request.json)

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
        wordlist = word_list.WordList.add(request.json)
        return {"id": wordlist.id, "message": "Word list created successfully"}, 200


class WordList(Resource):
    @auth_required("CONFIG_WORD_LIST_ACCESS")
    def get(self, word_list_id):
        word_list_result = word_list.WordList.get(word_list_id)
        if not word_list_result:
            return {"error": "Word list not found"}, 404
        return word_list_result.to_dict(), 200

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id):
        return word_list.WordList.delete(word_list_id)

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        return word_list.WordList.update(word_list_id, request.json)


class WordListImport(Resource):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        word_list.WordList.import_word_list(word_list_id, request.json)


class WordListExport(Resource):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def get(self):
        source_ids = request.args.getlist("ids")
        data = word_list.WordList.export(source_ids)
        if data is None:
            return "Unable to export", 400
        return send_file(
            io.BytesIO(data),
            download_name="word_list_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class WordListGather(Resource):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        return queue_manager.gather_word_list(word_list_id)


class Collectors(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return collector.Collector.get_all_json(search)


class Bots(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return bot.Bot.get_all_json(search)

    def put(self, bot_id):
        if updated_bot := bot.Bot.update(bot_id, request.json):
            return f"Successfully upated {updated_bot.id}", 200
        else:
            return "Error updateing", 500


class BotExecute(Resource):
    def post(self, bot_id):
        return queue_manager.execute_bot_task(bot_id)


class Parameters(Resource):
    def get(self):
        return parameter.Parameter.get_all_json()


class RefreshWorkers(Resource):
    def post(self):
        bots_manager.refresh_bots()


class QueueSchedule(Resource):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        try:
            if schedules := queue.ScheduleEntry.get_all():
                return [sched.to_dict() for sched in schedules], 200
            return {"message": "No schedules found"}, 404
        except Exception:
            logger.log_debug_trace()


class Workers(Resource):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.ping_workers()


class OSINTSources(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        result_dict = osint_source.OSINTSource.get_all_json(search)
        if result_dict["total_count"] == 0:
            return result_dict, 404
        return result_dict, 200

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        source = osint_source.OSINTSource.add(request.json)
        if not source:
            return "OSINT source could not be created", 400
        return {"id": source.id, "message": "OSINT source created successfully"}, 201


class OSINTSource(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self, source_id):
        if source := osint_source.OSINTSource.get(source_id):
            return source.to_dict(), 200
        return "OSINT source not found", 404

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id):
        if source := osint_source.OSINTSource.update(source_id, request.json):
            return f"OSINT Source {source.name} updated", 200
        return f"OSINT Source with ID: {source_id} not found", 404

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id):
        source = osint_source.OSINTSource.get(source_id)
        if not source:
            return f"OSINT Source with ID: {source_id} not found", 404
        osint_source.OSINTSource.delete(source_id)
        return f"OSINT Source {source.name} deleted", 200


class OSINTSourceCollect(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def post(self, source_id):
        return queue_manager.collect_osint_source(source_id)


class OSINTSourceCollectAll(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def post(self):
        return queue_manager.collect_all_osint_sources()


class OSINTSourcesExport(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        source_ids = request.args.getlist("ids")
        data = osint_source.OSINTSource.export_osint_sources(source_ids)
        if data is None:
            return "Unable to export", 400
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
            sources = osint_source.OSINTSource.import_osint_sources(file)
            if sources is None:
                return "Unable to import", 400
            return {"sources": [source.id for source in sources], "count": len(sources), "message": "Successfully imported sources"}
        return "No file provided", 400


class OSINTSourceGroups(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        source_group = osint_source.OSINTSourceGroup.add(request.json)
        return {"id": source_group.id, "message": "OSINT source group created successfully"}, 200


class OSINTSourceGroup(Resource):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id):
        return osint_source.OSINTSourceGroup.update(group_id, request.json)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id):
        return osint_source.OSINTSourceGroup.delete(group_id)


class Presenters(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return presenter.Presenter.get_all_json(search)


class Publishers(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher.Publisher.get_all_json(search)


class PublisherPresets(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        search = request.args.get(key="search", default=None)
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        pub_result = publisher_preset.PublisherPreset.add(request.json)
        return {"id": pub_result.id, "message": "Publisher preset created successfully"}, 200


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
        bot = bots_node.BotsNode.add(request.json)
        return {"id": bot.id, "message": "Bots node created successfully"}, 200

    @auth_required("CONFIG_BOTS_NODE_UPDATE")
    def put(self, node_id):
        return bots_manager.update_bots_node(node_id, request.json)

    @auth_required("CONFIG_BOTS_NODE_DELETE")
    def delete(self, node_id):
        return bots_node.BotsNode.delete(node_id)


def initialize(api: Api):
    namespace = Namespace("config", description="Configuration operations", path="/api/v1/config")

    namespace.add_resource(ACLEntries, "/acls")
    namespace.add_resource(ACLEntry, "/acls/<int:acl_id>")
    namespace.add_resource(Attribute, "/attributes/<int:attribute_id>")
    namespace.add_resource(Attributes, "/attributes")
    namespace.add_resource(AttributeEnum, "/attributes/<int:attribute_id>/enums/<int:enum_id>")
    namespace.add_resource(AttributeEnums, "/attributes/<int:attribute_id>/enums")
    namespace.add_resource(BotExecute, "/bots/<string:bot_id>/execute")
    namespace.add_resource(Bots, "/bots", "/bots/<string:bot_id>")
    namespace.add_resource(BotNodes, "/bots-nodes", "/bots-nodes/<string:node_id>")
    namespace.add_resource(Collectors, "/collectors", "/collectors/<string:collector_type>")
    namespace.add_resource(DictionariesReload, "/reload-enum-dictionaries/<string:dictionary_type>")
    namespace.add_resource(ExternalUser, "/external-users/<int:user_id>")
    namespace.add_resource(ExternalUsers, "/external-users")
    namespace.add_resource(Nodes, "/nodes", "/nodes/<string:node_id>")
    namespace.add_resource(Organization, "/organizations/<int:organization_id>")
    namespace.add_resource(Organizations, "/organizations")
    namespace.add_resource(OSINTSource, "/osint-sources/<string:source_id>")
    namespace.add_resource(OSINTSources, "/osint-sources")
    namespace.add_resource(OSINTSourceCollect, "/osint-sources/<string:source_id>/collect")
    namespace.add_resource(OSINTSourceCollectAll, "/osint-sources/collect")
    namespace.add_resource(OSINTSourceGroup, "/osint-source-groups/<string:group_id>")
    namespace.add_resource(OSINTSourceGroups, "/osint-source-groups")
    namespace.add_resource(OSINTSourcesExport, "/export-osint-sources")
    namespace.add_resource(OSINTSourcesImport, "/import-osint-sources")
    namespace.add_resource(Parameters, "/parameters")
    namespace.add_resource(Permissions, "/permissions")
    namespace.add_resource(Presenters, "/presenters")
    namespace.add_resource(ProductType, "/product-types/<int:type_id>")
    namespace.add_resource(ProductTypes, "/product-types")
    namespace.add_resource(PublisherPreset, "/publishers-presets/<string:preset_id>")
    namespace.add_resource(PublisherPresets, "/publishers-presets")
    namespace.add_resource(Publishers, "/publishers")
    namespace.add_resource(QueueSchedule, "/workers/schedule")
    namespace.add_resource(RefreshWorkers, "/workers/refresh")
    namespace.add_resource(ReportItemType, "/report-item-types/<int:type_id>")
    namespace.add_resource(ReportItemTypesConfig, "/report-item-types")
    namespace.add_resource(Role, "/roles/<int:role_id>")
    namespace.add_resource(Roles, "/roles")
    namespace.add_resource(User, "/users/<int:user_id>")
    namespace.add_resource(Users, "/users")
    namespace.add_resource(WordList, "/word-lists/<int:word_list_id>")
    namespace.add_resource(WordListExport, "/export-word-lists")
    namespace.add_resource(WordListGather, "/gather-word-list-entries/<int:word_list_id>")
    namespace.add_resource(WordListImport, "/import-word-lists")
    namespace.add_resource(WordLists, "/word-lists")
    namespace.add_resource(Workers, "/workers")

    api.add_namespace(namespace)
