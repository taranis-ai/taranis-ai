import io
from flask import request, send_file
from flask_restful import Resource

from core.managers import auth_manager, sse_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import ACLCheck, auth_required
from core.model import news_item, osint_source


class OSINTSourceGroupsAssess(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class OSINTSourceGroupsList(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_list_json(user=auth_manager.get_user_from_jwt(), acl_check=True)


class OSINTSourcesList(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSource.get_all_with_type()


class ManualOSINTSources(Resource):
    @auth_required(["ASSESS_ACCESS"])
    def get(self):
        return osint_source.OSINTSource.get_all_manual_json(auth_manager.get_user_from_jwt())


class AddNewsItem(Resource):
    @auth_required("ASSESS_CREATE")
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_item(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class NewsItems(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        user = auth_manager.get_user_from_jwt()

        try:
            filter_keys = ["search", "read", "important", "relevant", "in_analyze", "range", "sort"]
            filter_args = {k: v for k, v in request.args.items() if k in filter_keys}

            group_id = request.args.get("group", osint_source.OSINTSourceGroup.get_default().id)
            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return news_item.NewsItem.get_by_group_json(group_id, filter_args, offset, limit, user)


class NewsItemAggregates(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        user = auth_manager.get_user_from_jwt()

        try:
            filter_keys = ["search", "read", "important", "relevant", "in_analyze", "range", "sort"]
            filter_args = {k: v for k, v in request.args.items() if k in filter_keys}

            group_id = request.args.get("group", osint_source.OSINTSourceGroup.get_default().id)
            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return news_item.NewsItemAggregate.get_by_group_json(group_id, filter_args, offset, limit, user)


class NewsItemAggregatesByGroup(Resource):
    # DEPRECATED IN FAVOR OF NewsItemAggregates
    @auth_required("ASSESS_ACCESS")
    def get(self, group_id):
        user = auth_manager.get_user_from_jwt()

        try:
            filter_keys = ["search", "read", "important", "relevant", "in_analyze", "range", "sort"]
            filter_args = {k: v for k, v in request.args.items() if k in filter_keys}

            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return news_item.NewsItemAggregate.get_by_group_json(group_id, filter_args, offset, limit, user)


class NewsItem(Resource):
    @auth_required("ASSESS_ACCESS", ACLCheck.NEWS_ITEM_ACCESS)
    def get(self, item_id):
        return news_item.NewsItem.get_detail_json(item_id)

    @auth_required("ASSESS_UPDATE", ACLCheck.NEWS_ITEM_MODIFY)
    def put(self, item_id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required("ASSESS_DELETE", ACLCheck.NEWS_ITEM_MODIFY)
    def delete(self, item_id):
        response, code = news_item.NewsItem.delete(item_id)
        sse_manager.news_items_updated()
        return response, code


class NewsItemAggregate(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self, aggregate_id):
        return news_item.NewsItemAggregate.find(aggregate_id)

    @auth_required("ASSESS_UPDATE")
    def put(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItemAggregate.update(aggregate_id, request.json, user)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete(aggregate_id, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(Resource):
    @auth_required("ASSESS_UPDATE")
    def put(self):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.group_action(request.json, user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    def delete(self):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.group_action_delete(request.json, user)
        sse_manager.news_items_updated()
        return response, code


class DownloadAttachment(Resource):
    def get(self, item_data_id, attribute_id):
        if "jwt" in request.args:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is not None:
                permissions = user.get_permissions()
                if "ASSESS_ACCESS" in permissions:
                    attribute_mapping = news_item.NewsItemDataNewsItemAttribute.find(attribute_id)
                    need_check = attribute_mapping is not None
                    attribute = news_item.NewsItemAttribute.find(attribute_id)
                    if (
                        need_check
                        and item_data_id == attribute_mapping.news_item_data_id
                        and news_item.NewsItemData.allowed_with_acl(
                            attribute_mapping.news_item_data_id,
                            user,
                            False,
                            True,
                            False,
                        )
                    ):
                        logger.store_user_activity(user, "ASSESS_ACCESS", str({"file": attribute.value}))
                        return send_file(
                            io.BytesIO(attribute.binary_data),
                            attachment_filename=attribute.value,
                            mimetype=attribute.binary_mime_type,
                            as_attachment=True,
                        )
                    else:
                        logger.store_auth_error_activity("Unauthorized access attempt to News Item Data")
                else:
                    logger.store_auth_error_activity("Insufficient permissions")
            else:
                logger.store_auth_error_activity("Invalid JWT")
        else:
            logger.store_auth_error_activity("Missing JWT")


def initialize(api):
    api.add_resource(OSINTSourceGroupsAssess, "/api/v1/assess/osint-source-groups")
    api.add_resource(OSINTSourceGroupsList, "/api/v1/assess/osint-source-group-list")
    api.add_resource(OSINTSourcesList, "/api/v1/assess/osint-sources-list")
    api.add_resource(ManualOSINTSources, "/api/v1/assess/manual-osint-sources")
    api.add_resource(AddNewsItem, "/api/v1/assess/news-items")
    api.add_resource(
        NewsItemAggregatesByGroup,
        "/api/v1/assess/news-item-aggregates-by-group/<string:group_id>",
    )
    api.add_resource(
        NewsItemAggregates,
        "/api/v1/assess/news-item-aggregates",
    )
    api.add_resource(
        NewsItems,
        "/api/v1/assess/news-items",
    )
    api.add_resource(NewsItem, "/api/v1/assess/news-items/<int:item_id>")
    api.add_resource(NewsItemAggregate, "/api/v1/assess/news-item-aggregates/<int:aggregate_id>")
    api.add_resource(GroupAction, "/api/v1/assess/news-item-aggregates-group-action")
    api.add_resource(
        DownloadAttachment,
        "/api/v1/assess/news-item-data/<string:item_data_id>/attributes/<int:attribute_id>/file",
    )
