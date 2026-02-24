from flask import Blueprint, Flask, Response, request, send_file
from flask.views import MethodView
from sqlalchemy import select
from werkzeug.datastructures import FileStorage

from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.managers.auth_manager import api_key_required
from core.managers.db_manager import db
from core.managers.decorators import extract_args
from core.managers.sse_manager import sse_manager
from core.model.bot import Bot
from core.model.connector import Connector
from core.model.news_item_tag import NewsItemTag
from core.model.osint_source import OSINTSource
from core.model.product import Product
from core.model.product_type import ProductType
from core.model.publisher_preset import PublisherPreset
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.word_list import WordList


class AddNewsItems(MethodView):
    @api_key_required
    def post(self):
        json_data = request.json
        if not isinstance(json_data, list):
            return {"error": "Expected a list of news items"}, 400
        result, status = Story.add_news_items(json_data)
        sse_manager.news_items_updated()
        return result, status


class Products(MethodView):
    @api_key_required
    def get(self, product_id: str):
        return Product.get_for_worker(product_id)


class ProductsRender(MethodView):
    @api_key_required
    def get(self, product_id: str):
        if product_data := Product.get_render(product_id):
            return Response(product_data["blob"], headers={"Content-Type": product_data["mime_type"]}, status=200)
        return {"error": f"Product {product_id} not found"}, 404


class Presenters(MethodView):
    @api_key_required
    def get(self, presenter: str):
        try:
            if pres := ProductType.get(presenter):
                if tmpl := pres.get_template():
                    return send_file(tmpl)
            return {"error": f"Presenter with id {presenter} not found"}, 404
        except Exception:
            logger.exception()


class Publishers(MethodView):
    @api_key_required
    def get(self, publisher: str):
        return PublisherPreset.get_for_api(publisher)


class Sources(MethodView):
    @api_key_required
    def get(self, source_id: str | None = None):
        try:
            # Get all sources (for cron scheduler)
            if source_id is None:
                sources = OSINTSource.get_all_for_collector()
                return {"sources": [source.to_worker_dict() for source in sources]}, 200

            # Get specific source
            if not (source := OSINTSource.get(source_id)):
                return {"error": f"Source with id {source_id} not found"}, 404

            data = source.to_worker_dict()
            data_with_defaults = OSINTSource.get_with_defaults(data)
            return data_with_defaults, 200

        except Exception:
            logger.exception(f"Error fetching source {source_id}")
            return {"error": "Internal server error"}, 500


class CronJobs(MethodView):
    @api_key_required
    def get(self):
        """Get cron job configurations for the RQ scheduler (worker auth)."""
        try:
            cron_jobs = []

            sources = OSINTSource.get_all_for_collector()
            for source in sources:
                if cron_schedule := source.get_schedule():
                    cron_jobs.append(
                        {
                            "task": "collector_task",
                            "queue": "collectors",
                            "args": [source.id, False],
                            "cron": cron_schedule,
                            "task_id": source.task_id,
                            "name": source.name,
                        }
                    )

            stmt = select(Bot).where(Bot.enabled)
            bots = db.session.execute(stmt).scalars().all()
            for bot_item in bots:
                if cron_schedule := bot_item.get_schedule():
                    cron_jobs.append(
                        {
                            "task": "bot_task",
                            "queue": "bots",
                            "args": [bot_item.id],
                            "cron": cron_schedule,
                            "task_id": bot_item.task_id,
                            "name": bot_item.name,
                        }
                    )

            cron_jobs.append(
                {
                    "task": "cleanup_token_blacklist",
                    "queue": "misc",
                    "args": [],
                    "cron": "0 2 * * *",
                    "task_id": "cleanup_token_blacklist",
                    "name": "Cleanup Token Blacklist",
                }
            )

            return {"cron_jobs": cron_jobs}, 200
        except Exception:
            logger.exception("Failed to get cron job configurations")
            return {"error": "Failed to get cron job configurations"}, 500


class SourceIcon(MethodView):
    def put(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                file: FileStorage = request.files["file"]
                try:
                    source.update_icon(file.read())
                except ValueError as exc:
                    return {"error": str(exc)}, 400
                return {"message": "Icon uploaded"}, 200
            return {"error": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.exception()


class Stories(MethodView):
    @api_key_required
    def get(self):
        filter_keys = [
            "search",
            "source",
            "in_report",
            "timefrom",
            "sort",
            "range",
            "limit",
            "worker",
            "exclude_attr",
            "include_attr",
            "story_id",
            "cybersecurity",
        ]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
        filter_list_keys = ["source", "group"]
        for key in filter_list_keys:
            filter_args[key] = request.args.getlist(key)

        if story := Story.get_for_worker(filter_args):
            return story, 200
        return {"error": "No stories found"}, 404

    @api_key_required
    def post(self):
        return Story.add_or_update(request.json)


class MISPStories(MethodView):
    @api_key_required
    def post(self):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        if not isinstance(data, list):
            return {"error": "Expected a list of stories"}, 400
        result, status = Story.add_or_update_for_misp(data)
        sse_manager.news_items_updated()
        return result, status

    @api_key_required
    def put(self):
        data = request.json
        if not data:
            return {"error": "Missing story_ids or news_item_ids"}, 400
        result, code = {"error": "Couldn't get last changed"}, 500
        if story_ids := data.get("stories"):
            result, code = Connector.update_story_last_change(story_ids)
        if news_item_ids := data.get("news_items"):
            result, code = Connector.update_news_item_last_change(news_item_ids)
        sse_manager.news_items_updated()
        return result, code


class Tags(MethodView):
    @api_key_required
    def get(self):
        if tags := NewsItemTag.get_all_for_collector():
            return {tag.name: tag.to_dict() for tag in tags}, 200
        return {"error": "No tags found"}, 404

    @api_key_required
    def put(self):
        if not (data := request.json):
            return {"error": "No data provided"}, 400

        errors = {}
        if not isinstance(data, dict):
            return {"error": "Expected a dict for tags"}, 400
        for story_id, tags in data.items():
            story = Story.get(story_id)
            if not story:
                errors[story_id] = "Story not found"
                continue
            _, status = story.set_tags(tags)
            if status != 200:
                errors[story_id] = status
        if errors:
            return {"message": "Some tags failed to update", "errors": errors}, 207
        return {"message": "Tags updated"}, 200


class DropTags(MethodView):
    @api_key_required
    def post(self):
        return NewsItemTag.delete_all()


class BotInfo(MethodView):
    @api_key_required
    @extract_args("search", "fetch_all")
    def get(self, bot_id=None, filter_args=None):
        if not bot_id:
            return Bot.get_all_for_api(filter_args)

        if result := Bot.get(bot_id):
            return result.to_dict(), 200
        if result := Bot.filter_by_type(bot_id):
            return result.to_dict(), 200
        return {"error": f"Bot with id {bot_id} not found"}, 404

    @api_key_required
    def put(self, bot_id):
        return Bot.update(bot_id, request.json)


class PostCollectionBots(MethodView):
    @api_key_required
    def put(self):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        if source_id := data.get("source_id", None):
            return queue_manager.queue_manager.post_collection_bots(source_id=source_id)
        return {"error": "No source_id provided"}, 400


class WordLists(MethodView):
    @api_key_required
    @extract_args("search", "usage", "with_entries", "fetch_all")
    def get(self, word_list_id=None, filter_args=None):
        if word_list_id:
            return WordList.get_for_api(word_list_id)
        return WordList.get_all_for_api(filter_args)

    @api_key_required
    def put(self, word_list_id):
        if request.content_type == "application/json":
            content = request.json
        elif request.content_type == "text/csv":
            content = request.data.decode("utf-8")
        else:
            return {"error": "Unsupported content type"}, 400

        if not content:
            return {"error": "No content provided"}, 400

        if wls := WordList.update_word_list(content=content, content_type=request.content_type, word_list_id=word_list_id):
            return {"word_lists": f"{wls.id}", "message": "Successfully updated wordlist"}
        return {"error": "Unable to import"}, 400


class Connectors(MethodView):
    @api_key_required
    def get(self, connector_id: str):
        if connector := Connector.get(connector_id):
            return connector.to_dict(), 200
        return {"error": f"Connector with id {connector_id} not found"}, 404


class Reports(MethodView):
    @api_key_required
    def get(self, report_id: str):
        return ReportItem.get_for_api(report_id)


class TaskResults(MethodView):
    @api_key_required
    def put(self):
        """Save or update task result from worker."""
        from core.api.task import handle_task_specific_result
        from core.model.task import Task

        data = request.json
        if not data:
            return {"error": "No data provided"}, 400

        task_id = data.get("id")
        result = data.get("result")
        status = data.get("status")

        # Handle task-specific result processing (e.g., presenter results)
        if status == "SUCCESS" and result and task_id:
            handle_task_specific_result(task_id, result, status)

        return Task.add_or_update(data)


def initialize(app: Flask):
    worker_bp = Blueprint("worker", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/worker")

    worker_bp.add_url_rule("/osint-sources", view_func=Sources.as_view("osint_sources_all_worker"))
    worker_bp.add_url_rule("/osint-sources/<string:source_id>", view_func=Sources.as_view("osint_sources_worker"))
    worker_bp.add_url_rule("/osint-sources/<string:source_id>/icon", view_func=SourceIcon.as_view("osint_sources_worker_icon"))
    worker_bp.add_url_rule("/cron-jobs", view_func=CronJobs.as_view("cron_jobs_worker"))
    worker_bp.add_url_rule("/products/<string:product_id>", view_func=Products.as_view("products_worker"))
    worker_bp.add_url_rule("/products/<string:product_id>/render", view_func=ProductsRender.as_view("products_render_worker"))
    worker_bp.add_url_rule("/presenters/<string:presenter>", view_func=Presenters.as_view("presenters_worker"))
    worker_bp.add_url_rule("/publishers/<string:publisher>", view_func=Publishers.as_view("publishers_worker"))
    worker_bp.add_url_rule("/connectors/<string:connector_id>", view_func=Connectors.as_view("connectors_worker"))
    worker_bp.add_url_rule("/news-items", view_func=AddNewsItems.as_view("news_items_worker"))
    worker_bp.add_url_rule("/bots", view_func=BotInfo.as_view("bots_worker"))
    worker_bp.add_url_rule("/tags", view_func=Tags.as_view("tags_worker"))
    worker_bp.add_url_rule("/bots/<string:bot_id>", view_func=BotInfo.as_view("bot_info_worker"))
    worker_bp.add_url_rule("/post-collection-bots", view_func=PostCollectionBots.as_view("post_collection_bots_worker"))
    worker_bp.add_url_rule("/stories", view_func=Stories.as_view("stories_worker"))
    worker_bp.add_url_rule("/misp/stories", view_func=MISPStories.as_view("misp_stories_worker"))
    worker_bp.add_url_rule("/misp/last-change", view_func=MISPStories.as_view("last_change"))
    worker_bp.add_url_rule("/word-lists", view_func=WordLists.as_view("word_lists_worker"))
    worker_bp.add_url_rule("/word-list/<int:word_list_id>", view_func=WordLists.as_view("word_list_by_id_worker"))
    worker_bp.add_url_rule("/report-items/<string:report_id>", view_func=Reports.as_view("report_by_id_worker"))
    worker_bp.add_url_rule("/task-results", view_func=TaskResults.as_view("task_results_worker"))

    app.register_blueprint(worker_bp)
