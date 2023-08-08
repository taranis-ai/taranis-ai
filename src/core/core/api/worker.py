from flask import request
from flask_restx import Resource, Namespace, Api

from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.model.osint_source import OSINTSource
from core.model.osint_source import OSINTSourceGroup
from core.model.queue import ScheduleEntry
from core.model.word_list import WordList
from core.model.news_item import NewsItemAggregate, NewsItemTag
from core.model.bot import Bot


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


class Sources(Resource):
    @api_key_required
    def get(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                return source.to_collector_dict(), 200
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


class BotsInfo(Resource):
    @api_key_required
    def get(self):
        search = request.args.get(key="search", default=None)
        return Bot.get_all_json(search)


class NewsItemsAggregates(Resource):
    @api_key_required
    def get(self):
        filter_keys = ["search", "in_report", "timestamp", "sort", "source", "group"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}

        if aggregates := NewsItemAggregate.get_for_worker(filter_args):
            return aggregates, 200
        return {"error": "No news item aggregates found"}, 404


class Tags(Resource):
    @api_key_required
    def get(self):
        if tags := NewsItemTag.get_all():
            return {tag.name: tag.to_dict() for tag in tags}, 200
        return {"error": "No tags found"}, 404


class BotInfo(Resource):
    @api_key_required
    def get(self, bot_id):
        # return Bot.get(bot_id)
        # TODO: This is a hack to get the bot info by it's Type, not ID
        # depending on how the worker is triggered we might not have the bot I
        if result := Bot.get(bot_id):
            return result.to_bot_info_dict(), 200
        if result := Bot.filter_by_type(bot_id):
            return result.to_bot_info_dict(), 200
        return {"error": f"Bot with id {bot_id} not found"}, 404

    @api_key_required
    def put(self, bot_id):
        return Bot.update(bot_id, request.json)


class WordListBySourceGroup(Resource):
    @api_key_required
    def get(self, source_group: str):
        if osint_source_group := OSINTSourceGroup.get(source_group):
            return osint_source_group.to_word_list_dict()
        return {"error": f"Source group {source_group} not found"}, 404


class WordListByID(Resource):
    @api_key_required
    def get(self, word_list_id: int):
        if word_list := WordList.get(word_list_id):
            return word_list.to_dict()
        return {"error": f"Word list with id {word_list_id} not found"}, 404


def initialize(api: Api):
    worker_namespace = Namespace("Worker", description="Publish Subscribe Worker Endpoints", path="/api/v1/worker")
    beat_namespace = Namespace("Beat", description="Publish Subscribe Beat Endpoints", path="/api/v1/beat")
    beat_namespace.add_resource(
        QueueSchedule,
        "/schedule",
    )
    beat_namespace.add_resource(
        QueueScheduleEntry,
        "/schedule/<string:schedule_id>",
    )
    beat_namespace.add_resource(
        NextRunTime,
        "/next-run-time",
    )
    worker_namespace.add_resource(
        Sources,
        "/osint-sources/<string:source_id>",
    )
    worker_namespace.add_resource(BotsInfo, "/bots")
    worker_namespace.add_resource(Tags, "/tags")
    worker_namespace.add_resource(BotInfo, "/bots/<string:bot_id>")
    worker_namespace.add_resource(NewsItemsAggregates, "/news-item-aggregates")
    worker_namespace.add_resource(WordListBySourceGroup, "/word-lists-by-source-group/<string:source_group>")
    worker_namespace.add_resource(WordListByID, "/word-list/<int:word_list_id>")

    api.add_namespace(beat_namespace)
    api.add_namespace(worker_namespace)
