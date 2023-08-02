from celery import Celery
from flask import Flask

from core.managers.log_manager import logger
from core.model.queue import ScheduleEntry

queue_manager: "QueueManager"
periodic_tasks = [
    {"id": "cleanup_token_blacklist", "task": "worker.tasks.cleanup_token_blacklist", "schedule": "daily", "args": []},
]


class QueueManager:
    def __init__(self, app: Flask):
        self.celery = self.init_app(app)
        self.add_periodic_tasks()
        self.update_task_queue_from_osint_sources()

    def init_app(self, app: Flask):
        celery_app = Celery(app.name)
        celery_app.config_from_object(app.config["CELERY"])
        celery_app.set_default()
        app.extensions["celery"] = celery_app
        return celery_app

    def add_periodic_tasks(self):
        for task in periodic_tasks:
            ScheduleEntry.add_or_update(task)

    def update_task_queue_from_osint_sources(self):
        from core.model.osint_source import OSINTSource

        sources = OSINTSource.get_all()
        for source in sources:
            ScheduleEntry.add_or_update(source.to_task_dict())

    def ping_workers(self):
        result = self.celery.control.ping()
        workers = [{"name": list(worker.keys())[0], "status": list(list(worker.values())[0].keys())[0]} for worker in result]
        logger.info(f"Workers: {workers}")
        return workers


def initialize(app: Flask):
    global queue_manager
    queue_manager = QueueManager(app)
    logger.info(f"QueueManager initialized: {queue_manager.celery.broker_connection().as_uri()}")


def collect_osint_source(source_id: str):
    queue_manager.celery.send_task("worker.tasks.collect", args=[source_id])
    logger.info(f"Collect for source {source_id} scheduled")
    return {"message": f"Refresh for source {source_id} scheduled"}, 200


def collect_all_osint_sources():
    from core.model.osint_source import OSINTSource

    sources = OSINTSource.get_all()
    for source in sources:
        queue_manager.celery.send_task("worker.tasks.collect", args=[source.id])
        logger.info(f"Collect for source {source.id} scheduled")
    return {"message": f"Refresh for source {len(sources)} scheduled"}, 200


def gather_word_list(word_list_id: int):
    queue_manager.celery.send_task("worker.tasks.gather_word_list", args=[word_list_id])
    logger.info(f"Gathering for WordList {word_list_id} scheduled")
    return {"message": f"Gathering for WordList {word_list_id} scheduled"}, 200
