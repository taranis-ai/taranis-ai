from flask import request, send_file
from flask_restx import Resource, Namespace, Api
from werkzeug.datastructures import FileStorage

from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.managers import queue_manager
from core.model.osint_source import OSINTSource
from core.model.product import Product
from core.model.queue import ScheduleEntry
from core.model.product_type import ProductType
from core.model.publisher_preset import PublisherPreset
from core.model.word_list import WordList
from core.model.news_item import NewsItemAggregate, NewsItemTag
from core.managers.sse_manager import sse_manager
from core.model.bot import Bot


class AddNewsItems(Resource):
    @api_key_required
    def post(self):
        json_data = request.json
        result, status = NewsItemAggregate.add_news_items(json_data)
        sse_manager.news_items_updated()
        return result, status


class QueueScheduleEntry(Resource):
    @api_key_required
    def get(self, schedule_id: str):
        try:
            if schedule := ScheduleEntry.get(schedule_id):
                return schedule.to_worker_dict(), 200
            return {"error": f"Schedule with id {schedule_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class NextRunTime(Resource):
    @api_key_required
    def put(self):
        try:
            data = request.json
            if not data:
                return {"error": "No data provided"}, 400
            ScheduleEntry.update_next_run_time(data)
            return {"message": "Next run time updated"}, 200
        except Exception:
            logger.log_debug_trace()


class QueueSchedule(Resource):
    @api_key_required
    def get(self):
        try:
            if schedules := ScheduleEntry.get_all():
                return [sched.to_worker_dict() for sched in schedules], 200
            return {"error": "No schedules found"}, 404
        except Exception:
            logger.log_debug_trace()

    @api_key_required
    def put(self):
        try:
            data = request.json
            if not data:
                return {"error": "No data provided"}, 400
            entries = [ScheduleEntry.from_dict(entry) for entry in data]
            if not entries:
                return {"error": "No entries provided"}, 400
            return ScheduleEntry.sync(entries), 200
        except Exception:
            logger.log_debug_trace()


class Products(Resource):
    @api_key_required
    def get(self, product_id: int):
        try:
            if prod := Product.get(product_id):
                return prod.to_worker_dict(), 200
            return {"error": f"Product with id {product_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()

    @api_key_required
    def post(self, product_id: str):
        try:
            if render_result := request.data:
                return Product.update_render_for_id(product_id, render_result)

            return {"error": "Error reading file"}, 400
        except Exception:
            logger.log_debug_trace()

    @api_key_required
    def put(self, product_id: str):
        try:
            if render_result := request.data:
                return Product.update_render_for_id(product_id, render_result)

            return {"error": "Error reading file"}, 400
        except Exception:
            logger.log_debug_trace()


class Presenters(Resource):
    @api_key_required
    def get(self, presenter: str):
        try:
            if pres := ProductType.get(presenter):
                if tmpl := pres.get_template():
                    return send_file(tmpl)
            return {"error": f"Presenter with id {presenter} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class Publishers(Resource):
    @api_key_required
    def get(self, publisher: str):
        try:
            if pub := PublisherPreset.get(publisher):
                return pub.to_dict(), 200
            return {"error": f"Publisher with id {publisher} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class Sources(Resource):
    @api_key_required
    def get(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                return source.to_worker_dict(), 200
            return {"error": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()

    @api_key_required
    def put(self, source_id: str):
        try:
            source = OSINTSource.get(source_id)
            if not source:
                return {"error": f"OSINTSource with ID: {source_id} not found"}, 404

            error_msg = None
            if request.is_json:
                if request_json := request.json:
                    error_msg = request_json.get("error", None)

            source.update_status(error_msg)
            return {"message": "Status updated"}
        except Exception:
            logger.log_debug_trace()
            return {"error": "Could not update status"}, 500


class SourceIcon(Resource):
    def put(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                file: FileStorage = request.files["file"]
                source.update_icon(file.read())
                return {"message": "Icon uploaded"}, 200
            return {"error": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class BotsInfo(Resource):
    @api_key_required
    def get(self):
        search = request.args.get(key="search", default=None)
        return Bot.get_all_json(search)


class NewsItemsAggregates(Resource):
    @api_key_required
    def get(self):
        filter_keys = ["search", "in_report", "timestamp", "sort", "range"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
        filter_list_keys = ["source", "group"]
        for key in filter_list_keys:
            filter_args[key] = request.args.getlist(key)

        if aggregates := NewsItemAggregate.get_for_worker(filter_args):
            return aggregates, 200
        return {"error": "No news item aggregates found"}, 404


class Tags(Resource):
    @api_key_required
    def get(self):
        if tags := NewsItemTag.get_all():
            return {tag.name: tag.to_dict() for tag in tags}, 200
        return {"error": "No tags found"}, 404

    @api_key_required
    def put(self):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        errors = {}
        bot_type = request.args.get("bot_type", default="")
        for aggregate_id, tags in data.items():
            _, status = NewsItemAggregate.update_tags(aggregate_id, tags, bot_type)
            if status != 200:
                errors[aggregate_id] = status
        if errors:
            return {"message": "Some tags failed to update", "errors": errors}, 207
        return {"message": "Tags updated"}, 200


class DropTags(Resource):
    @api_key_required
    def post(self):
        NewsItemTag.delete_all_tags()
        return {"message": "deleted all tags"}, 200


class BotInfo(Resource):
    @api_key_required
    def get(self, bot_id):
        # return Bot.get(bot_id)
        # TODO: This is a hack to get the bot info by it's Type, not ID
        # depending on how the worker is triggered we might not have the bot I
        if result := Bot.get(bot_id):
            return result.to_dict(), 200
        if result := Bot.filter_by_type(bot_id):
            return result.to_dict(), 200
        return {"error": f"Bot with id {bot_id} not found"}, 404

    @api_key_required
    def put(self, bot_id):
        return Bot.update(bot_id, request.json)


class PostCollectionBots(Resource):
    @api_key_required
    def put(self):
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        if source_id := data.get("source_id", None):
            return queue_manager.queue_manager.post_collection_bots(source_id=source_id)
        return {"error": "No source_id provided"}, 400


class WordLists(Resource):
    @api_key_required
    def get(self):
        search = request.args.get(key="search", default=None)
        usage = request.args.get(key="usage", default=None, type=int)
        return WordList.get_all_json({"search": search, "usage": usage}, None, False)


class WordListByID(Resource):
    @api_key_required
    def get(self, word_list_id: int):
        if word_list := WordList.get(word_list_id):
            return word_list.to_dict()
        return {"error": f"Word list with id {word_list_id} not found"}, 404


class WordListUpdate(Resource):
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


def initialize(api: Api):
    worker_ns = Namespace("Worker", description="Publish Subscribe Worker Endpoints")
    beat_ns = Namespace("Beat", description="Publish Subscribe Beat Endpoints")
    beat_ns.add_resource(
        QueueSchedule,
        "/schedule",
    )
    beat_ns.add_resource(
        QueueScheduleEntry,
        "/schedule/<string:schedule_id>",
    )
    beat_ns.add_resource(
        NextRunTime,
        "/next-run-time",
    )
    worker_ns.add_resource(
        Sources,
        "/osint-sources/<string:source_id>",
    )
    worker_ns.add_resource(
        SourceIcon,
        "/osint-sources/<string:source_id>/icon",
    )
    worker_ns.add_resource(
        Products,
        "/products/<int:product_id>",
    )
    worker_ns.add_resource(
        Presenters,
        "/presenters/<string:presenter>",
    )
    worker_ns.add_resource(
        Publishers,
        "/publishers/<string:publisher>",
    )
    worker_ns.add_resource(AddNewsItems, "/news-items")
    worker_ns.add_resource(BotsInfo, "/bots")
    worker_ns.add_resource(Tags, "/tags")
    worker_ns.add_resource(DropTags, "/tags/drop")
    worker_ns.add_resource(BotInfo, "/bots/<string:bot_id>")
    worker_ns.add_resource(PostCollectionBots, "/post-collection-bots")
    worker_ns.add_resource(NewsItemsAggregates, "/news-item-aggregates", "/stories")
    worker_ns.add_resource(WordLists, "/word-lists")
    worker_ns.add_resource(WordListByID, "/word-list/<int:word_list_id>")
    worker_ns.add_resource(WordListUpdate, "/word-list/<int:word_list_id>/update")

    api.add_namespace(beat_ns, path="/beat")
    api.add_namespace(worker_ns, path="/worker")
