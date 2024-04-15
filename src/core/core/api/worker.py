from flask import request, send_file, Response, Flask
from flask.views import MethodView
from werkzeug.datastructures import FileStorage

from core.managers.auth_manager import api_key_required
from core.log import logger
from core.managers import queue_manager
from core.model.osint_source import OSINTSource
from core.model.product import Product
from core.model.queue import ScheduleEntry
from core.model.product_type import ProductType
from core.model.publisher_preset import PublisherPreset
from core.model.word_list import WordList
from core.model.news_item import NewsItemAggregate
from core.model.news_item_tag import NewsItemTag
from core.managers.sse_manager import sse_manager
from core.model.bot import Bot


class AddNewsItems(MethodView):
    @api_key_required
    def post(self):
        json_data = request.json
        result, status = NewsItemAggregate.add_news_items(json_data)
        sse_manager.news_items_updated()
        return result, status


class QueueScheduleEntry(MethodView):
    @api_key_required
    def get(self, schedule_id: str):
        try:
            if schedule := ScheduleEntry.get(schedule_id):
                return schedule.to_worker_dict(), 200
            return {"error": f"Schedule with id {schedule_id} not found"}, 404
        except Exception:
            logger.exception()


class NextRunTime(MethodView):
    @api_key_required
    def put(self):
        try:
            data = request.json
            if not data:
                return {"error": "No data provided"}, 400
            ScheduleEntry.update_next_run_time(data)
            return {"message": "Next run time updated"}, 200
        except Exception:
            logger.exception()


class QueueSchedule(MethodView):
    @api_key_required
    def get(self):
        try:
            if schedules := ScheduleEntry.get_all():
                return [sched.to_worker_dict() for sched in schedules], 200
            return {"error": "No schedules found"}, 404
        except Exception:
            logger.exception()

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
            logger.exception()


class Products(MethodView):
    @api_key_required
    def get(self, product_id: int):
        try:
            if prod := Product.get(product_id):
                return prod.to_worker_dict(), 200
            return {"error": f"Product with id {product_id} not found"}, 404
        except Exception:
            logger.exception()

    @api_key_required
    def put(self, product_id: str):
        try:
            if render_result := request.data:
                sse_manager.product_rendered({"id": product_id})
                return Product.update_render_for_id(product_id, render_result)

            return {"error": "Error reading file"}, 400
        except Exception:
            logger.exception()


class ProductsRender(MethodView):
    @api_key_required
    def get(self, product_id):
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
        try:
            if pub := PublisherPreset.get(publisher):
                return pub.to_dict(), 200
            return {"error": f"Publisher with id {publisher} not found"}, 404
        except Exception:
            logger.exception()


class Sources(MethodView):
    @api_key_required
    def get(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                return source.to_worker_dict(), 200
            return {"error": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.exception()

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
            logger.exception()
            return {"error": "Could not update status"}, 500


class SourceIcon(MethodView):
    def put(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                file: FileStorage = request.files["file"]
                source.update_icon(file.read())
                return {"message": "Icon uploaded"}, 200
            return {"error": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.exception()


class BotsInfo(MethodView):
    @api_key_required
    def get(self):
        search = request.args.get(key="search", default=None)
        return Bot.get_all_json(search)


class Stories(MethodView):
    @api_key_required
    def get(self):
        filter_keys = ["search", "in_report", "timefrom", "sort", "range", "limit"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
        filter_list_keys = ["source", "group"]
        for key in filter_list_keys:
            filter_args[key] = request.args.getlist(key)

        if aggregates := NewsItemAggregate.get_for_worker(filter_args):
            return aggregates, 200
        return {"error": "No news item aggregates found"}, 404


class Tags(MethodView):
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


class DropTags(MethodView):
    @api_key_required
    def post(self):
        return NewsItemTag.delete_all()


class BotInfo(MethodView):
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


class PostCollectionBots(MethodView):
    @api_key_required
    def put(self):
        data = request.json
        if not data:
            return {"error": "No data provided"}, 400
        if source_id := data.get("source_id", None):
            return queue_manager.queue_manager.post_collection_bots(source_id=source_id)
        return {"error": "No source_id provided"}, 400


class WordLists(MethodView):
    @api_key_required
    def get(self):
        search = request.args.get(key="search", default=None)
        usage = request.args.get(key="usage", default=None, type=int)
        return WordList.get_all_json({"search": search, "usage": usage}, None, False)


class WordListByID(MethodView):
    @api_key_required
    def get(self, word_list_id: int):
        if word_list := WordList.get(word_list_id):
            return word_list.to_dict()
        return {"error": f"Word list with id {word_list_id} not found"}, 404


class WordListUpdate(MethodView):
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


def initialize(app: Flask):
    worker_url = "/api/worker"
    beat_url = "/api/beat"

    app.add_url_rule(f"{beat_url}/schedule", view_func=QueueSchedule.as_view("queue_schedule"))
    app.add_url_rule(f"{beat_url}/schedule/<string:schedule_id>", view_func=QueueScheduleEntry.as_view("queue_schedule_entry"))
    app.add_url_rule(f"{beat_url}/next-run-time", view_func=NextRunTime.as_view("next_run_time"))
    app.add_url_rule(f"{worker_url}/osint-sources/<string:source_id>", view_func=Sources.as_view("osint_sources_worker"))
    app.add_url_rule(f"{worker_url}/osint-sources/<string:source_id>/icon", view_func=SourceIcon.as_view("osint_sources_worker_icon"))
    app.add_url_rule(f"{worker_url}/products/<int:product_id>", view_func=Products.as_view("products_worker"))
    app.add_url_rule(f"{worker_url}/products/<int:product_id>/render", view_func=ProductsRender.as_view("products_render_worker"))
    app.add_url_rule(f"{worker_url}/presenters/<string:presenter>", view_func=Presenters.as_view("presenters_worker"))
    app.add_url_rule(f"{worker_url}/publishers/<string:publisher>", view_func=Publishers.as_view("publishers_worker"))
    app.add_url_rule(f"{worker_url}/news-items", view_func=AddNewsItems.as_view("news_items_worker"))
    app.add_url_rule(f"{worker_url}/bots", view_func=BotsInfo.as_view("bots_worker"))
    app.add_url_rule(f"{worker_url}/tags", view_func=Tags.as_view("tags_worker"))
    app.add_url_rule(f"{worker_url}/bots/<string:bot_id>", view_func=BotInfo.as_view("bot_info_worker"))
    app.add_url_rule(f"{worker_url}/post-collection-bots", view_func=PostCollectionBots.as_view("post_collection_bots_worker"))
    app.add_url_rule(f"{worker_url}/stories", view_func=Stories.as_view("stories_worker"))
    app.add_url_rule(f"{worker_url}/word-lists", view_func=WordLists.as_view("word_lists_worker"))
    app.add_url_rule(f"{worker_url}/word-list/<int:word_list_id>", view_func=WordListByID.as_view("word_list_by_id_worker"))
    app.add_url_rule(f"{worker_url}/word-list/<int:word_list_id>/update", view_func=WordListUpdate.as_view("word_list_update_worker"))
