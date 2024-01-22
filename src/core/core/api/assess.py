import io
from flask import request, send_file
from flask_restx import Resource, Namespace
from urllib.parse import unquote

from core.managers import auth_manager
from core.managers.sse_manager import sse_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import auth_required
from core.model import news_item, osint_source, news_item_tag
from core.managers.input_validators import validate_id


class OSINTSourceGroupsAssess(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class OSINTSourceGroupsList(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(search=None, user=auth_manager.get_user_from_jwt(), acl_check=True)


class OSINTSourcesList(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSource.get_all_with_type()


class NewsItems(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        user = auth_manager.get_user_from_jwt()

        try:
            filter_keys = ["search" "read", "important", "relevant", "in_analyze", "range", "sort"]
            filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

            filter_args["limit"] = min(int(request.args.get("limit", 20)), 1000)
            page = int(request.args.get("page", 0))
            filter_args["offset"] = min(int(request.args.get("offset", page * filter_args["limit"])), (2**31) - 1)
            return news_item.NewsItem.get_by_filter_json(filter_args, user)
        except Exception as ex:
            logger.log_debug(ex)
            return {"error": "Failed to get Newsitems"}, 500

    @auth_required("ASSESS_CREATE")
    def post(self):
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 422
        data_json = request.json
        if not data_json:
            return {"error": "No data in JSON"}, 422

        result, status = news_item.NewsItemAggregate.add_news_items([data_json])
        sse_manager.news_items_updated()
        return result, status


class NewsItem(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self, item_id):
        item = news_item.NewsItem.get(item_id)
        return item.to_dict() if item else ("NewsItem not found", 404)

    @auth_required("ASSESS_UPDATE")
    def put(self, item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "Invalid User"}, 403
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400
        response, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    def patch(self, item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "Invalid User"}, 403
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400
        response, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, item_id):
        response, code = news_item.NewsItem.delete(item_id)
        sse_manager.news_items_updated()
        return response, code


class Stories(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            filter_keys = ["search", "read", "unread", "important", "relevant", "in_report", "range", "sort"]
            filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
            filter_list_keys = ["source", "group"]
            for key in filter_list_keys:
                filter_args[key] = request.args.getlist(key)

            filter_args["limit"] = min(int(request.args.get("limit", 20)), 1000)
            tags = request.args.getlist("tags")
            filter_args["tags"] = [unquote(t) for t in tags]
            page = int(request.args.get("page", 0))
            filter_args["offset"] = min(int(request.args.get("offset", page * filter_args["limit"])), (2**31) - 1)

            logger.debug(filter_args)
            return news_item.NewsItemAggregate.get_by_filter_json(filter_args, auth_manager.get_user_from_jwt())
        except Exception:
            logger.exception("Failed to get Stories")
            return {"error": "Failed to get Stories"}, 400


class StoryTags(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            search = request.args.get("search", None)
            limit = min(int(request.args.get("limit", 20)), 200)
            offset = min(int(request.args.get("offset", 0)), (2**31) - 1)
            default_min_size = 0 if search else 3
            min_size = int(request.args.get("min_size", default_min_size))
            filter_args = {"limit": limit, "offset": offset, "search": search, "min_size": min_size}
            return news_item_tag.NewsItemTag.get_json(filter_args)
        except Exception as ex:
            logger.log_debug(ex)
            return {"error": "Failed to get Tags"}, 400


class StoryTagList(Resource):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            search = request.args.get("search", "")
            limit = min(int(request.args.get("limit", 20)), 200)
            offset = min(int(request.args.get("offset", 0)), (2**31) - 1)
            filter_args = {"limit": limit, "offset": offset, "search": search}
            return news_item_tag.NewsItemTag.get_list(filter_args)
        except Exception as ex:
            logger.log_debug(ex)
            return {"error": "Failed to get Tags"}, 400


class Story(Resource):
    @auth_required("ASSESS_ACCESS")
    @validate_id("aggregate_id")
    def get(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        return news_item.NewsItemAggregate.get_json(aggregate_id, user)

    @auth_required("ASSESS_UPDATE")
    @validate_id("aggregate_id")
    def put(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400
        response, code = news_item.NewsItemAggregate.update(aggregate_id, request.json, user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    @validate_id("aggregate_id")
    def delete(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete_by_id(aggregate_id, user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_id("aggregate_id")
    def patch(self, aggregate_id):
        user = auth_manager.get_user_from_jwt()
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400
        response, code = news_item.NewsItemAggregate.update(aggregate_id, request.json, user)
        return response, code


class UnGroupAction(Resource):
    @auth_required("ASSESS_UPDATE")
    def put(self):
        user = auth_manager.get_user_from_jwt()
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400

        newsitem_ids = request.json
        if not newsitem_ids:
            return {"error": "No news item ids provided"}, 400
        response, code = news_item.NewsItemAggregate.remove_news_items_from_story(newsitem_ids, user)
        sse_manager.news_items_updated()
        return response, code


class UnGroupStories(Resource):
    @auth_required("ASSESS_UPDATE")
    def put(self):
        user = auth_manager.get_user_from_jwt()
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400

        story_ids = request.json
        if not story_ids:
            return {"error": "No story ids provided"}, 400
        response, code = news_item.NewsItemAggregate.ungroup_multiple_stories(story_ids, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(Resource):
    @auth_required("ASSESS_UPDATE")
    def put(self):
        user = auth_manager.get_user_from_jwt()
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400

        aggregate_ids = request.json
        if not aggregate_ids:
            return {"error": "No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_aggregate(aggregate_ids, user)
        sse_manager.news_items_updated()
        return response, code


class DownloadAttachment(Resource):
    @auth_required("ASSESS_ACCESS")
    @validate_id("item_data_id")
    @validate_id("attribute_id")
    def get(self, item_data_id, attribute_id):
        user = auth_manager.get_user_from_jwt()
        if attribute := news_item.NewsItemAttribute.get(attribute_id):
            logger.store_user_activity(user, "ASSESS_ACCESS", str({"file": attribute.value}))
            return (
                send_file(
                    io.BytesIO(attribute.binary_data),
                    download_name=attribute.value,
                    mimetype=attribute.binary_mime_type,
                    as_attachment=True,
                ),
                200,
            )
        return {"error": "Unauthorized access attempt to News Item Data"}, 400


def initialize(api):
    namespace = Namespace("Assess", description="Assess related operations")
    namespace.add_resource(OSINTSourceGroupsAssess, "/osint-source-groups")
    namespace.add_resource(OSINTSourceGroupsList, "/osint-source-group-list")
    namespace.add_resource(OSINTSourcesList, "/osint-sources-list")
    namespace.add_resource(Stories, "/news-item-aggregates", "/stories")
    namespace.add_resource(StoryTags, "/tags")
    namespace.add_resource(StoryTagList, "/taglist")

    namespace.add_resource(NewsItems, "/news-items")
    namespace.add_resource(NewsItem, "/news-items/<int:item_id>")
    namespace.add_resource(Story, "/news-item-aggregates/<int:aggregate_id>", "/stories/<int:aggregate_id>")
    namespace.add_resource(GroupAction, "/news-item-aggregates/group", "/stories/group")
    namespace.add_resource(UnGroupStories, "/news-item-aggregates/ungroup", "/stories/ungroup")
    namespace.add_resource(UnGroupAction, "/news-items/ungroup")
    namespace.add_resource(
        DownloadAttachment,
        "/news-item-data/<string:item_data_id>/attributes/<int:attribute_id>/file",
    )
    api.add_namespace(namespace, path="/assess")
