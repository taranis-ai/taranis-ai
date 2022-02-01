import io
from flask import request, send_file
from flask_restful import Resource

from managers import auth_manager, sse_manager, log_manager
from managers.auth_manager import ACLCheck, auth_required
from model import news_item, osint_source
from model.permission import Permission


class OSINTSourceGroupsAssess(Resource):

    @auth_required('ASSESS_ACCESS')
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class ManualOSINTSources(Resource):

    @auth_required(['ASSESS_ACCESS'])
    def get(self):
        return osint_source.OSINTSource.get_all_manual_json(auth_manager.get_user_from_jwt())


class AddNewsItem(Resource):

    @auth_required('ASSESS_CREATE')
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_item(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class NewsItemsByGroup(Resource):

    @auth_required('ASSESS_ACCESS', ACLCheck.OSINT_SOURCE_GROUP_ACCESS)
    def get(self, group_id):
        user = auth_manager.get_user_from_jwt()

        try:
            filter = {}
            if 'search' in request.args and request.args['search']:
                filter['search'] = request.args['search']
            if 'read' in request.args and request.args['read']:
                filter['read'] = request.args['read']
            if 'important' in request.args and request.args['important']:
                filter['important'] = request.args['important']
            if 'relevant' in request.args and request.args['relevant']:
                filter['relevant'] = request.args['relevant']
            if 'in_analyze' in request.args and request.args['in_analyze']:
                filter['in_analyze'] = request.args['in_analyze']
            if 'range' in request.args and request.args['range']:
                filter['range'] = request.args['range']
            if 'sort' in request.args and request.args['sort']:
                filter['sort'] = request.args['sort']

            offset = None
            if 'offset' in request.args and request.args['offset']:
                offset = int(request.args['offset'])

            limit = 50
            if 'limit' in request.args and request.args['limit']:
                limit = min(int(request.args['limit']), 200)
        except Exception as ex:
            log_manager.log_debug(ex)
            return "", 400

        return news_item.NewsItemAggregate.get_by_group_json(group_id, filter, offset, limit, user)


class NewsItem(Resource):

    @auth_required('ASSESS_ACCESS', ACLCheck.NEWS_ITEM_ACCESS)
    def get(self, item_id):
        return news_item.NewsItem.get_detail_json(item_id)

    @auth_required('ASSESS_UPDATE', ACLCheck.NEWS_ITEM_MODIFY)
    def put(self, item_id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required('ASSESS_DELETE', ACLCheck.NEWS_ITEM_MODIFY)
    def delete(self, item_id):
        response, code = news_item.NewsItem.delete(item_id)
        sse_manager.news_items_updated()
        return response, code


class NewsItemAggregate(Resource):

    @auth_required('ASSESS_UPDATE')
    def put(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItemAggregate.update(aggregate_id, request.json, user)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required('ASSESS_DELETE')
    def delete(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete(aggregate_id, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(Resource):

    @auth_required('ASSESS_UPDATE')
    def put(self):
        user = auth_manager.get_user_from_jwt()
        if request.json['action'] == 'DELETE':
            response, code = news_item.NewsItemAggregate.group_action_delete(request.json, user)
            sse_manager.news_items_updated()
            return response, code
        else:
            response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, user)
            sse_manager.news_items_updated()
            if len(osint_source_ids) > 0:
                sse_manager.remote_access_news_items_updated(osint_source_ids)
            return response, code


class DownloadAttachment(Resource):

    def get(self, item_data_id, attribute_id):
        if 'jwt' in request.args:
            user = auth_manager.decode_user_from_jwt(request.args['jwt'])
            if user is not None:
                permissions = user.get_permissions()
                if 'ASSESS_ACCESS' in permissions:
                    attribute_mapping = news_item.NewsItemDataNewsItemAttribute.find(attribute_id)
                    need_check = False
                    if attribute_mapping is not None:
                        need_check = True
                    attribute = news_item.NewsItemAttribute.find(attribute_id)
                    if need_check and item_data_id == attribute_mapping.news_item_data_id and news_item.NewsItemData.allowed_with_acl(
                            attribute_mapping.news_item_data_id, user, False, True, False):
                        log_manager.store_user_activity(user, "ASSESS_ACCESS", str({'file': attribute.value}))
                        return send_file(
                            io.BytesIO(attribute.binary_data),
                            attachment_filename=attribute.value,
                            mimetype=attribute.binary_mime_type,
                            as_attachment=True
                        )
                    else:
                        log_manager.store_auth_error_activity("Unauthorized access attempt to News Item Data")
                else:
                    log_manager.store_auth_error_activity("Insufficient permissions")
            else:
                log_manager.store_auth_error_activity("Invalid JWT")
        else:
            log_manager.store_auth_error_activity("Missing JWT")


def initialize(api):
    api.add_resource(OSINTSourceGroupsAssess, "/api/v1/assess/osint-source-groups")
    api.add_resource(ManualOSINTSources, "/api/v1/assess/manual-osint-sources")
    api.add_resource(AddNewsItem, "/api/v1/assess/news-items")
    api.add_resource(NewsItemsByGroup, "/api/v1/assess/news-item-aggregates-by-group/<string:group_id>")
    api.add_resource(NewsItem, "/api/v1/assess/news-items/<int:item_id>")
    api.add_resource(NewsItemAggregate, "/api/v1/assess/news-item-aggregates/<int:aggregate_id>")
    api.add_resource(GroupAction, "/api/v1/assess/news-item-aggregates-group-action")
    api.add_resource(DownloadAttachment,
                     "/api/v1/assess/news-item-data/<string:item_data_id>/attributes/<int:attribute_id>/file")

    Permission.add("ASSESS_ACCESS", "Assess access", "Access to Assess module")
    Permission.add("ASSESS_CREATE", "Assess create", "Create news item")
    Permission.add("ASSESS_UPDATE", "Assess update", "Update news item")
    Permission.add("ASSESS_DELETE", "Assess delete", "Delete news item")
