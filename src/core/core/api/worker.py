from flask import Blueprint, request, send_file, Response, Flask
from flask.views import MethodView
from werkzeug.datastructures import FileStorage

from core.managers.auth_manager import api_key_required
from core.log import logger
from core.managers import queue_manager
from core.model.connector import Connector
from core.model.osint_source import OSINTSource
from core.model.product import Product
from core.model.product_type import ProductType
from core.model.publisher_preset import PublisherPreset
from core.model.word_list import WordList
from core.model.story import Story
from core.model.news_item_tag import NewsItemTag
from core.managers.sse_manager import sse_manager
from core.model.bot import Bot
from core.managers.decorators import extract_args
from core.config import Config


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
        bot_type = request.args.get("bot_type", default="")
        for story_id, tags in data.items():
            _, status = Story.update_tags(story_id, tags, bot_type)
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
    @extract_args("search")
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
    @extract_args("search", "usage", "with_entries")
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


def initialize(app: Flask):
    worker_bp = Blueprint("worker", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/worker")

    worker_bp.add_url_rule("/osint-sources/<string:source_id>", view_func=Sources.as_view("osint_sources_worker"))
    worker_bp.add_url_rule("/osint-sources/<string:source_id>/icon", view_func=SourceIcon.as_view("osint_sources_worker_icon"))
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
    worker_bp.add_url_rule("/word-lists", view_func=WordLists.as_view("word_lists_worker"))
    worker_bp.add_url_rule("/word-list/<int:word_list_id>", view_func=WordLists.as_view("word_list_by_id_worker"))

    app.register_blueprint(worker_bp)
