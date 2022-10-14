import io

from flask import request, send_file
from flask_restful import Resource

from managers import auth_manager, sse_manager, remote_manager, presenters_manager, \
    publishers_manager, bots_manager, external_auth_manager, log_manager, collectors_manager
from managers.auth_manager import auth_required, get_user_from_jwt
from model import acl_entry, remote, presenters_node, publisher_preset, publishers_node, \
    bots_node, bot_preset, attribute, collectors_node, organization, osint_source, product_type, \
    report_item_type, role, user, word_list
from model.news_item import NewsItemAggregate
from model.permission import Permission
from schema.role import PermissionSchema


class DictionariesReload(Resource):

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def get(self, dictionary_type):
        attribute.Attribute.load_dictionaries(dictionary_type)
        return "success", 200


class Attributes(Resource):

    @auth_required('CONFIG_ATTRIBUTE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return attribute.Attribute.get_all_json(search)

    @auth_required('CONFIG_ATTRIBUTE_CREATE')
    def post(self):
        try:
            attribute.Attribute.add_attribute(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create attribute")
            return "", 400


class Attribute(Resource):

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def put(self, attribute_id):
        try:
            attribute.Attribute.update(attribute_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update attribute")
            return "", 400

    @auth_required('CONFIG_ATTRIBUTE_DELETE')
    def delete(self, attribute_id):
        try:
            return attribute.Attribute.delete_attribute(attribute_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete attribute")
            return "", 400


class AttributeEnums(Resource):

    @auth_required('CONFIG_ATTRIBUTE_ACCESS')
    def get(self, attribute_id):
        search = None
        offset = 0
        limit = 10
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        if 'offset' in request.args and request.args['offset']:
            offset = request.args['offset']
        if 'limit' in request.args and request.args['limit']:
            limit = request.args['limit']
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)

    @auth_required('CONFIG_ATTRIBUTE_CREATE')
    def post(self, attribute_id):
        try:
            attribute.AttributeEnum.add(attribute_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create attribute enum")
            return "", 400


class AttributeEnum(Resource):
    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def put(self, attribute_id, enum_id):
        try:
            attribute.AttributeEnum.update(enum_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update attribute enum")
            return "", 400

    @auth_required('CONFIG_ATTRIBUTE_DELETE')
    def delete(self, attribute_id, enum_id):
        try:
            return attribute.AttributeEnum.delete(enum_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete attribute enum")
            return "", 400


class ReportItemTypesConfig(Resource):

    @auth_required('CONFIG_REPORT_TYPE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return report_item_type.ReportItemType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required('CONFIG_REPORT_TYPE_CREATE')
    def post(self):
        try:
            report_item_type.ReportItemType.add_report_item_type(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create report type")
            return "", 400


class ReportItemType(Resource):

    @auth_required('CONFIG_REPORT_TYPE_UPDATE')
    def put(self, type_id):
        try:
            report_item_type.ReportItemType.update(type_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update report type")
            return "", 400

    @auth_required('CONFIG_REPORT_TYPE_DELETE')
    def delete(self, type_id):
        try:
            return report_item_type.ReportItemType.delete_report_item_type(type_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete report type")
            return "", 400


class ProductTypes(Resource):

    @auth_required('CONFIG_PRODUCT_TYPE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required('CONFIG_PRODUCT_TYPE_CREATE')
    def post(self):
        try:
            product_type.ProductType.add_new(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create product type")
            return "", 400


class ProductType(Resource):

    @auth_required('CONFIG_PRODUCT_TYPE_UPDATE')
    def put(self, type_id):
        try:
            product_type.ProductType.update(type_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update product type")
            return "", 400

    @auth_required('CONFIG_PRODUCT_TYPE_DELETE')
    def delete(self, type_id):
        try:
            return product_type.ProductType.delete(type_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete product type")
            return "", 400


class Permissions(Resource):

    @auth_required('CONFIG_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return Permission.get_all_json(search)


class ExternalPermissions(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def get(self):
        permissions = auth_manager.get_external_permissions()
        permissions_schema = PermissionSchema(many=True)
        return {'total_count': len(permissions), 'items': permissions_schema.dump(permissions)}


class Roles(Resource):

    @auth_required('CONFIG_ROLE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return role.Role.get_all_json(search)

    @auth_required('CONFIG_ROLE_CREATE')
    def post(self):
        try:
            role.Role.add_new(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create role")
            return "", 400


class Role(Resource):

    @auth_required('CONFIG_ROLE_UPDATE')
    def put(self, role_id):
        try:
            role.Role.update(role_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update role")
            return "", 400

    @auth_required('CONFIG_ROLE_DELETE')
    def delete(self, role_id):
        try:
            return role.Role.delete(role_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete role")
            return "", 400


class ACLEntries(Resource):

    @auth_required('CONFIG_ACL_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return acl_entry.ACLEntry.get_all_json(search)

    @auth_required('CONFIG_ACL_CREATE')
    def post(self):
        try:
            acl_entry.ACLEntry.add_new(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create acl entry")
            return "", 400


class ACLEntry(Resource):

    @auth_required('CONFIG_ACL_UPDATE')
    def put(self, acl_id):
        try:
            acl_entry.ACLEntry.update(acl_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update acl entry")
            return "", 400

    @auth_required('CONFIG_ACL_DELETE')
    def delete(self, acl_id):
        try:
            return acl_entry.ACLEntry.delete(acl_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete acl entry")
            return "", 400


class Organizations(Resource):

    @auth_required('CONFIG_ORGANIZATION_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return organization.Organization.get_all_json(search)

    @auth_required('CONFIG_ORGANIZATION_CREATE')
    def post(self):
        try:
            organization.Organization.add_new(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create organization")
            return "", 400


class Organization(Resource):

    @auth_required('CONFIG_ORGANIZATION_UPDATE')
    def put(self, organization_id):
        try:
            organization.Organization.update(organization_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update organization")
            return "", 400

    @auth_required('CONFIG_ORGANIZATION_DELETE')
    def delete(self, organization_id):
        try:
            return organization.Organization.delete(organization_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete organization")
            return "", 400


class Users(Resource):

    @auth_required('CONFIG_USER_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return user.User.get_all_json(search)

    @auth_required('CONFIG_USER_CREATE')
    def post(self):
        try:
            external_auth_manager.create_user(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create user in external auth system")
            return "", 400

        user.User.add_new(request.json)


class User(Resource):

    @auth_required('CONFIG_USER_UPDATE')
    def put(self, user_id):
        original_user = user.User.find_by_id(user_id)
        original_username = original_user.username

        try:
            external_auth_manager.update_user(request.json, original_username)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update user in external auth system")
            return "", 400

        user.User.update(user_id, request.json)

    @auth_required('CONFIG_USER_DELETE')
    def delete(self, user_id):
        original_user = user.User.find_by_id(user_id)
        original_username = original_user.username

        user.User.delete(user_id)

        try:
            external_auth_manager.delete_user(original_username)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete user in external auth system")
            return "", 400


class ExternalUsers(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)

    @auth_required('MY_ASSETS_CONFIG')
    def post(self):
        try:
            permissions = auth_manager.get_external_permissions_ids()
            user.User.add_new_external(auth_manager.get_user_from_jwt(), permissions, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create external user")
            return "", 400


class ExternalUser(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def put(self, user_id):
        try:
            permissions = auth_manager.get_external_permissions_ids()
            user.User.update_external(auth_manager.get_user_from_jwt(), permissions, user_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update external user")
            return "", 400

    @auth_required('MY_ASSETS_CONFIG')
    def delete(self, user_id):
        try:
            return user.User.delete_external(auth_manager.get_user_from_jwt(), user_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete external user")
            return "", 400


class WordLists(Resource):

    @auth_required('CONFIG_WORD_LIST_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return word_list.WordList.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required('CONFIG_WORD_LIST_CREATE')
    def post(self):
        try:
            word_list.WordList.add_new(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create word list")
            return "", 400


class WordList(Resource):

    @auth_required('CONFIG_WORD_LIST_DELETE')
    def delete(self, word_list_id):
        try:
            return word_list.WordList.delete(word_list_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete word list")
            return "", 400

    @auth_required('CONFIG_WORD_LIST_UPDATE')
    def put(self, word_list_id):
        try:
            word_list.WordList.update(word_list_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update word list")
            return "", 400


class CollectorsNodes(Resource):

    @auth_required('CONFIG_COLLECTORS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return collectors_node.CollectorsNode.get_all_json(search)

    @auth_required('CONFIG_COLLECTORS_NODE_CREATE')
    def post(self):
        try:
            return '', collectors_manager.add_collectors_node(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create collectors node")
            return "", 400


class CollectorsNode(Resource):

    @auth_required('CONFIG_COLLECTORS_NODE_UPDATE')
    def put(self, node_id):
        try:
            collectors_manager.update_collectors_node(node_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update collectors node")
            return "", 400

    @auth_required('CONFIG_COLLECTORS_NODE_DELETE')
    def delete(self, node_id):
        try:
            collectors_node.CollectorsNode.delete(node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete collectors node")
            return "", 400


class OSINTSources(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return osint_source.OSINTSource.get_all_json(search)

    @auth_required('CONFIG_OSINT_SOURCE_CREATE')
    def post(self):
        try:
            collectors_manager.add_osint_source(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create OSINT source")
            return "", 400


class OSINTSource(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_UPDATE')
    def put(self, source_id):
        try:
            updated_osint_source, default_group = collectors_manager.update_osint_source(source_id, request.json)
            if default_group is not None:
                NewsItemAggregate.reassign_to_new_groups(updated_osint_source.id, default_group.id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update OSINT source")
            return "", 400

    @auth_required('CONFIG_OSINT_SOURCE_DELETE')
    def delete(self, source_id):
        try:
            collectors_manager.delete_osint_source(source_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete OSINT source")
            return "", 400


class OSINTSourcesExport(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_ACCESS')
    def post(self):
        try:
            data = collectors_manager.export_osint_sources(request.json)
            return send_file(
                io.BytesIO(data),
                attachment_filename="osint_sources_export.json",
                mimetype="application/json",
                as_attachment=True
            )
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not export OSINT source")
            return "", 400


class OSINTSourcesImport(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_CREATE')
    def post(self):
        try:
            file = request.files.get('file')
            if file:
                collectors_node_id = request.form['collectors_node_id']
                collectors_manager.import_osint_sources(collectors_node_id, file)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not import OSINT source")
            return "", 400


class OSINTSourceGroups(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_CREATE')
    def post(self):
        try:
            osint_source.OSINTSourceGroup.add(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create OSINT source group")
            return "", 400


class OSINTSourceGroup(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_UPDATE')
    def put(self, group_id):
        try:
            sources_in_default_group, message, code = osint_source.OSINTSourceGroup.update(group_id, request.json)
            if sources_in_default_group is not None:
                default_group = osint_source.OSINTSourceGroup.get_default()
                for source in sources_in_default_group:
                    NewsItemAggregate.reassign_to_new_groups(source.id, default_group.id)
            return message, code
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update OSINT source group")
            return "", 400


    @auth_required('CONFIG_OSINT_SOURCE_GROUP_DELETE')
    def delete(self, group_id):
        try:
            return osint_source.OSINTSourceGroup.delete(group_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete OSINT source group")
            return "", 400


class RemoteAccesses(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return remote.RemoteAccess.get_all_json(search)

    @auth_required('CONFIG_REMOTE_ACCESS_CREATE')
    def post(self):
        try:
            remote.RemoteAccess.add(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create remmote access")
            return "", 400


class RemoteAccess(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_UPDATE')
    def put(self, remote_access_id):
        try:
            event_id, disconnect = remote.RemoteAccess.update(remote_access_id, request.json)
            if disconnect:
                sse_manager.remote_access_disconnect([event_id])
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update remmote access")
            return "", 400

        @auth_required('CONFIG_REMOTE_ACCESS_DELETE')
        def delete(self, remote_access_id):
            try:
                return remote.RemoteAccess.delete(remote_access_id)
            except Exception as ex:
                log_manager.log_critical(ex)
                log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete remmote access")
                return "", 400


class RemoteNodes(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return remote.RemoteNode.get_all_json(search)

    @auth_required('CONFIG_REMOTE_ACCESS_CREATE')
    def post(self):
        try:
            remote.RemoteNode.add(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create remmote node")
            return "", 400


class RemoteNode(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_UPDATE')
    def put(self, remote_node_id):
        try:
            if remote.RemoteNode.update(id, request.json) is False:
                remote_manager.disconnect_from_node(remote_node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update remmote node")
            return "", 400


    @auth_required('CONFIG_REMOTE_ACCESS_DELETE')
    def delete(self, remote_node_id):
        try:
            remote_manager.disconnect_from_node(remote_node_id)
            return remote.RemoteNode.delete(id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete remmote node")
            return "", 400


class RemoteNodeConnect(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self, remote_node_id):
        try:
            return remote_manager.connect_to_node(remote_node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not connect to node")
            return "", 400


class PresentersNodes(Resource):

    @auth_required('CONFIG_PRESENTERS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return presenters_node.PresentersNode.get_all_json(search)

    @auth_required('CONFIG_PRESENTERS_NODE_CREATE')
    def post(self):
        try:
            return '', presenters_manager.add_presenters_node(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create preseters node")
            return "", 400


class PresentersNode(Resource):

    @auth_required('CONFIG_PRESENTERS_NODE_UPDATE')
    def put(self, node_id):
        try:
            presenters_manager.update_presenters_node(node_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update preseters node")
            return "", 400

    @auth_required('CONFIG_PRESENTERS_NODE_DELETE')
    def delete(self, node_id):
        try:
            return presenters_node.PresentersNode.delete(node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete preseters node")
            return "", 400


class PublisherNodes(Resource):

    @auth_required('CONFIG_PUBLISHERS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return publishers_node.PublishersNode.get_all_json(search)

    @auth_required('CONFIG_PUBLISHERS_NODE_CREATE')
    def post(self):
        try:
            return '', publishers_manager.add_publishers_node(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create publishers node")
            return "", 400


class PublishersNode(Resource):

    @auth_required('CONFIG_PUBLISHERS_NODE_UPDATE')
    def put(self, node_id):
        try:
            publishers_manager.update_publishers_node(node_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update publishers node")
            return "", 400

    @auth_required('CONFIG_PUBLISHERS_NODE_DELETE')
    def delete(self, node_id):
        try:
            return publishers_node.PublishersNode.delete(node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete publishers node")
            return "", 400


class PublisherPresets(Resource):

    @auth_required('CONFIG_PUBLISHER_PRESET_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required('CONFIG_PUBLISHER_PRESET_CREATE')
    def post(self):
        try:
            publishers_manager.add_publisher_preset(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create publishers preset")
            return "", 400


class PublisherPreset(Resource):

    @auth_required('CONFIG_PUBLISHER_PRESET_UPDATE')
    def put(self, preset_id):
        try:
            publisher_preset.PublisherPreset.update(preset_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update publishers preset")
            return "", 400

    @auth_required('CONFIG_PUBLISHER_PRESET_DELETE')
    def delete(self, preset_id):
        try:
            return publisher_preset.PublisherPreset.delete(preset_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete publishers preset")
            return "", 400


class BotNodes(Resource):

    @auth_required('CONFIG_BOTS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return bots_node.BotsNode.get_all_json(search)

    @auth_required('CONFIG_BOTS_NODE_CREATE')
    def post(self):
        try:
            return '', bots_manager.add_bots_node(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create bots node")
            return "", 400


class BotsNode(Resource):

    @auth_required('CONFIG_BOTS_NODE_UPDATE')
    def put(self, node_id):
        try:
            bots_manager.update_bots_node(node_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update bots node")
            return "", 400

    @auth_required('CONFIG_BOTS_NODE_DELETE')
    def delete(self, node_id):
        try:
            return bots_node.BotsNode.delete(node_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete bots node")
            return "", 400


class BotPresets(Resource):

    @auth_required('CONFIG_BOT_PRESET_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return bot_preset.BotPreset.get_all_json(search)

    @auth_required('CONFIG_BOT_PRESET_CREATE')
    def post(self):
        try:
            bots_manager.add_bot_preset(request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create bots preset")
            return "", 400


class BotPreset(Resource):

    @auth_required('CONFIG_BOT_PRESET_UPDATE')
    def put(self, preset_id):
        try:
            bot_preset.BotPreset.update(preset_id, request.json)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update bots preset")
            return "", 400

    @auth_required('CONFIG_BOT_PRESET_DELETE')
    def delete(self, preset_id):
        try:
            return bot_preset.BotPreset.delete(preset_id)
        except Exception as ex:
            log_manager.log_critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete bots preset")
            return "", 400


def initialize(api):
    api.add_resource(DictionariesReload, "/api/v1/config/reload-enum-dictionaries/<string:dictionary_type>")
    api.add_resource(Attributes, "/api/v1/config/attributes")
    api.add_resource(Attribute, "/api/v1/config/attributes/<int:attribute_id>")
    api.add_resource(AttributeEnums, "/api/v1/config/attributes/<int:attribute_id>/enums")
    api.add_resource(AttributeEnum, "/api/v1/config/attributes/<int:attribute_id>/enums/<int:enum_id>")

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

    api.add_resource(CollectorsNodes, "/api/v1/config/collectors-nodes")
    api.add_resource(CollectorsNode, "/api/v1/config/collectors-nodes/<string:node_id>")
    api.add_resource(OSINTSources, "/api/v1/config/osint-sources")
    api.add_resource(OSINTSource, "/api/v1/config/osint-sources/<string:source_id>")
    api.add_resource(OSINTSourcesExport, "/api/v1/config/export-osint-sources")
    api.add_resource(OSINTSourcesImport, "/api/v1/config/import-osint-sources")
    api.add_resource(OSINTSourceGroups, "/api/v1/config/osint-source-groups")
    api.add_resource(OSINTSourceGroup, "/api/v1/config/osint-source-groups/<string:group_id>")

    api.add_resource(RemoteAccesses, "/api/v1/config/remote-accesses")
    api.add_resource(RemoteAccess, "/api/v1/config/remote-accesses/<int:remote_access_id>")

    api.add_resource(RemoteNodes, "/api/v1/config/remote-nodes")
    api.add_resource(RemoteNode, "/api/v1/config/remote-nodes/<int:remote_node_id>")
    api.add_resource(RemoteNodeConnect, "/api/v1/config/remote-nodes/<int:remote_node_id>/connect")

    api.add_resource(PresentersNodes, "/api/v1/config/presenters-nodes")
    api.add_resource(PresentersNode, "/api/v1/config/presenters-nodes/<string:node_id>")

    api.add_resource(PublisherNodes, "/api/v1/config/publishers-nodes")
    api.add_resource(PublishersNode, "/api/v1/config/publishers-nodes/<string:node_id>")

    api.add_resource(PublisherPresets, "/api/v1/config/publishers-presets")
    api.add_resource(PublisherPreset, "/api/v1/config/publishers-presets/<string:preset_id>")

    api.add_resource(BotNodes, "/api/v1/config/bots-nodes")
    api.add_resource(BotsNode, "/api/v1/config/bots-nodes/<string:node_id>")

    api.add_resource(BotPresets, "/api/v1/config/bots-presets")
    api.add_resource(BotPreset, "/api/v1/config/bots-presets/<string:preset_id>")

    Permission.add("CONFIG_ACCESS", "Configuration access", "Access to Configuration module")

    Permission.add("CONFIG_ORGANIZATION_ACCESS", "Config organizations access", "Access to attributes configuration")
    Permission.add("CONFIG_ORGANIZATION_CREATE", "Config organization create", "Create organization configuration")
    Permission.add("CONFIG_ORGANIZATION_UPDATE", "Config organization update", "Update organization configuration")
    Permission.add("CONFIG_ORGANIZATION_DELETE", "Config organization delete", "Delete organization configuration")

    Permission.add("CONFIG_USER_ACCESS", "Config users access", "Access to users configuration")
    Permission.add("CONFIG_USER_CREATE", "Config user create", "Create user configuration")
    Permission.add("CONFIG_USER_UPDATE", "Config user update", "Update user configuration")
    Permission.add("CONFIG_USER_DELETE", "Config user delete", "Delete user configuration")

    Permission.add("CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration")
    Permission.add("CONFIG_ROLE_CREATE", "Config role create", "Create role configuration")
    Permission.add("CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration")
    Permission.add("CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration")

    Permission.add("CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration")
    Permission.add("CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration")
    Permission.add("CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration")
    Permission.add("CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration")

    Permission.add("CONFIG_PRODUCT_TYPE_ACCESS", "Config product types access", "Access to product types configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_CREATE", "Config product type create", "Create product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_UPDATE", "Config product type update", "Update product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_DELETE", "Config product type delete", "Delete product type configuration")

    Permission.add("CONFIG_ATTRIBUTE_ACCESS", "Config attributes access", "Access to attributes configuration")
    Permission.add("CONFIG_ATTRIBUTE_CREATE", "Config attribute create", "Create attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_UPDATE", "Config attribute update", "Update attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_DELETE", "Config attribute delete", "Delete attribute configuration")

    Permission.add("CONFIG_REPORT_TYPE_ACCESS", "Config report item types access",
                   "Access to report item types configuration")
    Permission.add("CONFIG_REPORT_TYPE_CREATE", "Config report item type create",
                   "Create report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_UPDATE", "Config report item type update",
                   "Update report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_DELETE", "Config report item type delete",
                   "Delete report item type configuration")

    Permission.add("CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    Permission.add("CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    Permission.add("CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    Permission.add("CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")

    Permission.add("CONFIG_COLLECTORS_NODE_ACCESS", "Config collectors nodes access",
                   "Access to collectors nodes configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_CREATE", "Config collectors node create",
                   "Create collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_UPDATE", "Config collectors node update",
                   "Update collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_DELETE", "Config collectors node delete",
                   "Delete collectors node configuration")

    Permission.add("CONFIG_OSINT_SOURCE_ACCESS", "Config OSINT source access", "Access to OSINT sources configuration")
    Permission.add("CONFIG_OSINT_SOURCE_CREATE", "Config OSINT source create", "Create OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_UPDATE", "Config OSINT source update", "Update OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_DELETE", "Config OSINT source delete", "Delete OSINT source configuration")

    Permission.add("CONFIG_OSINT_SOURCE_GROUP_ACCESS", "Config OSINT source group access",
                   "Access to OSINT sources groups configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_CREATE", "Config OSINT source group create",
                   "Create OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_UPDATE", "Config OSINT source group update",
                   "Update OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_DELETE", "Config OSINT source group delete",
                   "Delete OSINT source group configuration")

    Permission.add("CONFIG_REMOTE_ACCESS_ACCESS", "Config remote access access",
                   "Access to remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_CREATE", "Config remote access create", "Create remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_UPDATE", "Config remote access update", "Update remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_DELETE", "Config remote access delete", "Delete remote access configuration")

    Permission.add("CONFIG_REMOTE_NODE_ACCESS", "Config remote nodes access",
                   "Access to remote nodes configuration")
    Permission.add("CONFIG_REMOTE_NODE_CREATE", "Config remote node create", "Create remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_UPDATE", "Config remote node update", "Update remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_DELETE", "Config remote node delete", "Delete remote node configuration")

    Permission.add("CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access",
                   "Access to presenters nodes configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create",
                   "Create presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update",
                   "Update presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete",
                   "Delete presenters node configuration")

    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access",
                   "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create",
                   "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update",
                   "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete",
                   "Delete publishers node configuration")

    Permission.add("CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access",
                   "Access to publisher presets configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create",
                   "Create publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update",
                   "Update publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete",
                   "Delete publisher preset configuration")

    Permission.add("CONFIG_BOTS_NODE_ACCESS", "Config bots nodes access", "Access to bots nodes configuration")
    Permission.add("CONFIG_BOTS_NODE_CREATE", "Config bots node create", "Create bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_UPDATE", "Config bots node update", "Update bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_DELETE", "Config bots node delete", "Delete bots node configuration")

    Permission.add("CONFIG_BOT_PRESET_ACCESS", "Config bot presets access", "Access to bot presets configuration")
    Permission.add("CONFIG_BOT_PRESET_CREATE", "Config bot preset create", "Create bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_UPDATE", "Config bot preset update", "Update bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_DELETE", "Config bot preset delete", "Delete bot preset configuration")
