from flask import Blueprint, request, Flask
from flask.views import MethodView
from urllib.parse import unquote
from flask_jwt_extended import current_user

from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model import news_item, osint_source, news_item_tag, story
from core.managers.decorators import validate_json
from core.managers import queue_manager
from core.service.news_item import NewsItemService
from core.audit import audit_logger
from core.config import Config
from core.model.story_conflict import StoryConflict


class OSINTSourceGroupsList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_for_assess_api(user=current_user)


class OSINTSourcesList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSource.get_all_for_assess_api(user=current_user)


class NewsItems(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        filter_keys = ["search", "read", "important", "relevant", "in_analyze", "range", "sort"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        filter_args["limit"] = min(int(request.args.get("limit", 20)), 1000)
        page = int(request.args.get("page", 0))
        filter_args["offset"] = min(int(request.args.get("offset", page * filter_args["limit"])), (2**31) - 1)
        return news_item.NewsItem.get_all_for_api(filter_args, current_user)

    @auth_required("ASSESS_CREATE")
    @validate_json
    def post(self):
        data_json = request.json
        if not data_json:
            return {"error": "No NewsItems in JSON Body"}, 422

        data_json["osint_source_id"] = "manual"
        result, status = story.Story.add_single_news_item(data_json)
        sse_manager.news_items_updated()
        return result, status


class NewsItem(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, item_id):
        return news_item.NewsItem.get_for_api(item_id, current_user)

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, item_id):
        response, code = NewsItemService.update(item_id, request.json, current_user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, item_id):
        response, code = NewsItemService.update(item_id, request.json, current_user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, item_id):
        response, code = NewsItemService.delete(item_id, current_user)
        sse_manager.news_items_updated()
        return response, code


class UpdateNewsItemAttributes(MethodView):
    @auth_required("ASSESS_UPDATE")
    def put(self, news_item_id):
        return news_item.NewsItem.update_attributes(news_item_id, request.json)


class Stories(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            filter_keys = [
                "search",
                "read",
                "unread",
                "important",
                "cybersecurity",
                "relevant",
                "in_report",
                "range",
                "sort",
                "timefrom",
                "timeto",
                "no_count",
                "exclude_attr",
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

            return story.Story.get_by_filter_json(filter_args, current_user)
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
            return news_item_tag.NewsItemTag.get_filtered_tags(filter_args)
        except Exception:
            logger.exception()
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
        except Exception:
            logger.exception()
            return {"error": "Failed to get Tags"}, 400


class Story(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id: str):
        return story.Story.get_for_api(story_id, current_user)

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, story_id):
        response, code = story.Story.update(story_id, request.json, current_user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, story_id):
        response, code = story.Story.delete_by_id(story_id, current_user)
        sse_manager.news_items_updated()
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, story_id):
        response, code = story.Story.update(story_id, request.json, current_user)
        return response, code


class UnGroupNewsItem(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (newsitem_ids := request.json):
            return {"error": "No news item ids provided"}, 400
        response, code = story.Story.remove_news_items_from_story(newsitem_ids, current_user)
        sse_manager.news_items_updated()
        return response, code


class UnGroupStories(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (story_ids := request.json):
            return {"error": "No story ids provided"}, 400
        response, code = story.Story.ungroup_multiple_stories(story_ids, current_user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (story_ids := request.json):
            return {"error": "No story ids provided"}, 400
        response, code = story.Story.group_stories(story_ids, current_user)
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


class Connectors(MethodView):
    @auth_required("CONNECTOR_USER_ACCESS")
    @validate_json
    def post(self, connector_id):
        """Send stories to an external system."""
        if not request.json:
            return {"error": "Invalid JSON payload"}, 400

        story_ids = request.json.get("story_ids")
        if not story_ids:
            return {"error": "No story_id provided"}, 400

        try:
            response, code = queue_manager.queue_manager.push_to_connector(connector_id=connector_id, story_ids=story_ids)
            return response, code
        except Exception as e:
            return {"error": str(e)}, 500

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, story_id):
        if not request.json:
            return {"error": "Invalid JSON payload"}, 400
        if not story_id:
            return {"error": "No story_id provided"}, 400

        conflict = StoryConflict.conflict_store.get(story_id)
        if conflict is None:
            logger.error(f"No conflict found for story {story_id}")
            return {"error": "No conflict found", "id": story_id}, 404

        response, code = conflict.resolve(request.json, user=current_user)
        return response, code


class Proposals(MethodView):
    @auth_required("CONNECTOR_USER_ACCESS")
    def get(self):
        return {"count": StoryConflict.get_proposal_count()}, 200


def initialize(app: Flask):
    assess_bp = Blueprint("assess", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/assess")

    assess_bp.add_url_rule("/stories", view_func=Stories.as_view("stories"))
    assess_bp.add_url_rule("/story/<string:story_id>", view_func=Story.as_view("story"))
    assess_bp.add_url_rule("/story/<string:connector_id>/share", view_func=Connectors.as_view("share_to_connector"))
    assess_bp.add_url_rule("/osint-source-group-list", view_func=OSINTSourceGroupsList.as_view("osint_source_groups-list"))
    assess_bp.add_url_rule("/osint-sources-list", view_func=OSINTSourcesList.as_view("osint_sources_list"))
    assess_bp.add_url_rule("/tags", view_func=StoryTags.as_view("tags"))
    assess_bp.add_url_rule("/taglist", view_func=StoryTagList.as_view("taglist"))
    assess_bp.add_url_rule("/news-items", view_func=NewsItems.as_view("news_items"))
    assess_bp.add_url_rule("/news-items/<string:item_id>", view_func=NewsItem.as_view("news_item"))
    assess_bp.add_url_rule(
        "/news-items/<string:news_item_id>/attributes", view_func=UpdateNewsItemAttributes.as_view("update_news_item_attributes")
    )
    assess_bp.add_url_rule("/stories/group", view_func=GroupAction.as_view("group_action"))
    assess_bp.add_url_rule("/stories/ungroup", view_func=UnGroupStories.as_view("ungroup_stories"))
    assess_bp.add_url_rule("/news-items/ungroup", view_func=UnGroupNewsItem.as_view("ungroup_news_items"))
    assess_bp.add_url_rule("/stories/botactions", view_func=BotActions.as_view("bot_actions"))
    assess_bp.add_url_rule("/connectors/story/<string:story_id>", view_func=Connectors.as_view("connectors"))
    assess_bp.add_url_rule("/connectors/proposals", view_func=Proposals.as_view("proposals"))

    assess_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(assess_bp)
