from flask import request, Flask
from flask.views import MethodView
from urllib.parse import unquote

from core.managers import auth_manager
from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model import news_item, osint_source, news_item_tag
from core.managers.input_validators import validate_id, validate_json
from core.managers import queue_manager


class OSINTSourceGroupsList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(search=None, user=auth_manager.get_user_from_jwt(), acl_check=True)


class OSINTSourcesList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSource.get_all_with_type(search=None, user=auth_manager.get_user_from_jwt(), acl_check=True)


class NewsItems(MethodView):
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
    @validate_json
    def post(self):
        data_json = request.json
        if not data_json:
            return {"error": "No NewsItems in JSON Body"}, 422

        result, status = news_item.NewsItemAggregate.add_news_items([data_json])
        sse_manager.news_items_updated()
        return result, status


class NewsItem(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, item_id):
        item = news_item.NewsItem.get(item_id)
        return item.to_dict() if item else ("NewsItem not found", 404)

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "Invalid User"}, 403
        response, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "Invalid User"}, 403
        response, code = news_item.NewsItem.update(item_id, request.json, user.id)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, item_id):
        response, code = news_item.NewsItem.delete(item_id)
        sse_manager.news_items_updated()
        return response, code


class Stories(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            filter_keys = [
                "search",
                "read",
                "unread",
                "important",
                "relevant",
                "in_report",
                "range",
                "sort",
                "timefrom",
                "timeto",
                "no_count",
                "include_attrs",
                "exclude_attrs",
            ]
            filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
            filter_list_keys = ["source", "group"]
            for key in filter_list_keys:
                filter_args[key] = request.args.getlist(key)

            filter_args["limit"] = min(int(request.args.get("limit", 20)), 400)
            tags = request.args.getlist("tags")
            filter_args["tags"] = [unquote(t) for t in tags]
            page = int(request.args.get("page", 0))
            offset = int(request.args.get("offset", page * filter_args["limit"]))
            filter_args["offset"] = min(offset, (2**31) - 1)

            logger.debug(filter_args)
            return news_item.NewsItemAggregate.get_by_filter_json(filter_args, auth_manager.get_user_from_jwt())
        except Exception:
            logger.exception("Failed to get Stories")
            return {"error": "Failed to get Stories"}, 400


class StoryTags(MethodView):
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


class StoryTagList(MethodView):
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


class Story(MethodView):
    @auth_required("ASSESS_ACCESS")
    @validate_id("story_id")
    def get(self, story_id):
        user = auth_manager.get_user_from_jwt()
        return news_item.NewsItemAggregate.get_json(story_id, user)

    @auth_required("ASSESS_UPDATE")
    @validate_id("story_id")
    @validate_json
    def put(self, story_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.update(story_id, request.json, user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    @validate_id("story_id")
    def delete(self, story_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete_by_id(story_id, user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_id("story_id")
    @validate_json
    def patch(self, story_id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.update(story_id, request.json, user)
        return response, code


class UnGroupNewsItem(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        user = auth_manager.get_user_from_jwt()

        newsitem_ids = request.json
        if not newsitem_ids:
            return {"error": "No news item ids provided"}, 400
        response, code = news_item.NewsItemAggregate.remove_news_items_from_story(newsitem_ids, user)
        sse_manager.news_items_updated()
        return response, code


class UnGroupStories(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        user = auth_manager.get_user_from_jwt()
        story_ids = request.json
        if not story_ids:
            return {"error": "No story ids provided"}, 400
        response, code = news_item.NewsItemAggregate.ungroup_multiple_stories(story_ids, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        user = auth_manager.get_user_from_jwt()
        aggregate_ids = request.json
        if not aggregate_ids:
            return {"error": "No aggregate ids provided"}, 400
        response, code = news_item.NewsItemAggregate.group_aggregate(aggregate_ids, user)
        sse_manager.news_items_updated()
        return response, code


class BotActions(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def post(self):
        if not request.json:
            return {"error": "Please provide story_id & bot_id"}, 400
        bot_id = request.json.get("bot_id")
        if not bot_id:
            return {"error": "No bot_id provided"}, 400
        story_id = request.json.get("story_id")
        if not story_id:
            return {"error": "No story_id provided"}, 400
        response, code = queue_manager.queue_manager.execute_bot_task(bot_id=bot_id, filter={"story_id": story_id})
        sse_manager.news_items_updated()
        return response, code


def initialize(app: Flask):
    base_route = "/api/assess"
    app.add_url_rule(f"{base_route}/stories", view_func=Stories.as_view("stories"))
    app.add_url_rule(f"{base_route}/story/<int:story_id>", view_func=Story.as_view("story"))
    app.add_url_rule(f"{base_route}/osint-source-group-list", view_func=OSINTSourceGroupsList.as_view("osint_source_groups-list"))
    app.add_url_rule(f"{base_route}/osint-sources-list", view_func=OSINTSourcesList.as_view("osint_sources_list"))
    app.add_url_rule(f"{base_route}/tags", view_func=StoryTags.as_view("tags"))
    app.add_url_rule(f"{base_route}/taglist", view_func=StoryTagList.as_view("taglist"))
    app.add_url_rule(f"{base_route}/news-items", view_func=NewsItems.as_view("news_items"))
    app.add_url_rule(f"{base_route}/news-items/<int:item_id>", view_func=NewsItem.as_view("news_item"))
    app.add_url_rule(f"{base_route}/stories/group", view_func=GroupAction.as_view("group_action"))
    app.add_url_rule(f"{base_route}/stories/ungroup", view_func=UnGroupStories.as_view("ungroup_stories"))
    app.add_url_rule(f"{base_route}/news-items/ungroup", view_func=UnGroupNewsItem.as_view("ungroup_news_items"))
    app.add_url_rule(f"{base_route}/stories/botactions", view_func=BotActions.as_view("bot_actions"))
