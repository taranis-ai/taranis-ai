from flask import request
from flask_restx import Resource, Namespace

from core.managers.auth_manager import api_key_required
from core.managers.log_manager import logger
from core.model.osint_source import OSINTSource
from core.model.queue import ScheduleEntry
from core.model.news_item import NewsItemAggregate
from core.model.bot import Bot


class QueueScheduleEntry(Resource):
    @api_key_required
    def get(self, schedule_id: str):
        try:
            if schedule := ScheduleEntry.get(schedule_id):
                return schedule.to_worker_dict(), 200
            return {"message": f"Schedule with id {schedule_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class NextRunTime(Resource):
    @api_key_required
    def put(self):
        try:
            data = request.json
            if not data:
                return {"message": "No data provided"}, 400
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
            return {"message": "No schedules found"}, 404
        except Exception:
            logger.log_debug_trace()

    @api_key_required
    def put(self):
        try:
            data = request.json
            if not data:
                return {"message": "No data provided"}, 400
            entries = [ScheduleEntry.from_dict(entry) for entry in data]
            if not entries:
                return {"message": "No entries provided"}, 400
            return ScheduleEntry.sync(entries), 200
        except Exception:
            logger.log_debug_trace()


class Sources(Resource):
    @api_key_required
    def get(self, source_id: str):
        try:
            if source := OSINTSource.get(source_id):
                return source.to_collector_dict(), 200
            return {"message": f"Source with id {source_id} not found"}, 404
        except Exception:
            logger.log_debug_trace()


class BotsInfo(Resource):
    def get(self):
        search = request.args.get(key="search", default=None)
        return Bot.get_all_json(search)


class NewsItemsAggregates(Resource):
    @api_key_required
    def get(self):
        filter_keys = ["search", "in_report", "timestamp", "sort", "source", "group"]
        filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}

        return NewsItemAggregate.get_for_worker(filter_args)


class BotInfo(Resource):
    def get(self, bot_id):
        # return Bot.get(bot_id)
        # TODO: This is a hack to get the bot info by it's Type, not ID
        # depending on how the worker is triggered we might not have the bot ID
        return Bot.filter_by_type(bot_id).to_bot_info_dict()

    def put(self, bot_id):
        return Bot.update(bot_id, request.json)


def initialize(api):
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
    worker_namespace.add_resource(BotInfo, "/bots/<string:bot_id>")
    worker_namespace.add_resource(NewsItemsAggregates, "/news-item-aggregates")

    api.add_namespace(beat_namespace)
    api.add_namespace(worker_namespace)
