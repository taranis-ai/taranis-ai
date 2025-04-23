from celery import Celery
from flask import Flask
import requests
import contextlib
from requests.auth import HTTPBasicAuth

from core.log import logger
from kombu.exceptions import OperationalError
from kombu import Queue


queue_manager: "QueueManager"


class QueueManager:
    def __init__(self, app: Flask):
        self._celery: Celery = self.init_app(app)
        self.error: str = ""
        self.mgmt_api = f"http://{app.config['QUEUE_BROKER_HOST']}:15672/api/"
        self.queue_user = app.config["QUEUE_BROKER_USER"]
        self.queue_password = app.config["QUEUE_BROKER_PASSWORD"]
        self.queue_names = ["misc", "bots", "celery", "collectors", "presenters", "publishers", "connectors"]

    def init_app(self, app: Flask):
        celery_app = Celery("taranis-ai")
        celery_app.config_from_object(app.config["CELERY"])
        celery_app.set_default()
        app.extensions["celery"] = celery_app
        return celery_app

    def post_init(self):
        self.clear_queues()
        self.update_task_queue_from_osint_sources()
        self.schedule_word_list_gathering()

    def clear_queues(self):
        with self._celery.connection() as conn:
            for queue_name in set(self.queue_names):
                with contextlib.suppress(Exception):
                    queue = Queue(name=queue_name, channel=conn)
                    queue.purge()
            logger.info("All queues cleared")

    @property
    def celery(self) -> Celery:
        return self._celery

    def update_task_queue_from_osint_sources(self):
        from core.model.osint_source import OSINTSource

        [source.schedule_osint_source() for source in OSINTSource.get_all_for_collector()]

    def schedule_word_list_gathering(self):
        from core.model.word_list import WordList

        word_lists = WordList.get_all_empty() or []
        for word_list in word_lists:
            self._celery.send_task("gather_word_list", args=[word_list.id], task_id=f"gather_word_list_{word_list.id}", queue="misc")

    def get_queued_tasks(self):
        if self.error:
            return {"error": "QueueManager not initialized"}, 500
        response = requests.get(f"{self.mgmt_api}queues/", auth=HTTPBasicAuth(self.queue_user, self.queue_password), timeout=5)
        if not response.ok:
            logger.error(response.text)
            return {"error": "Could not reach rabbitmq"}, 500
        tasks = [{key: d[key] for key in ("messages", "name") if key in d} for d in response.json()]
        logger.debug(f"Queued tasks: {tasks}")
        return tasks, 200

    def ping_workers(self):
        if self.error:
            logger.error("QueueManager not initialized")
            return {"error": "QueueManager not initialized"}, 500
        try:
            result = self._celery.control.ping()
            self.error = ""
            return [
                {
                    "name": list(worker.keys())[0],
                    "status": list(list(worker.values())[0].keys())[0],
                }
                for worker in result
            ]
        except Exception:
            self.error = "Could not reach rabbitmq"
            return {"error": "Could not reach rabbitmq"}, 500

    def send_task(self, *args, **kwargs):
        if self.error:
            return False
        self._celery.send_task(*args, **kwargs)
        return True

    def get_queue_status(self) -> tuple[dict, int]:
        if self.error:
            return {"error": "Could not reach rabbitmq", "url": ""}, 500
        return {"status": "🚀 Up and running 🏃", "url": f"{self._celery.broker_connection().as_uri()}"}, 200

    def get_task(self, task_id) -> tuple[dict, int]:
        if self.error:
            return {"error": "Could not reach rabbitmq"}, 500
        task = self._celery.AsyncResult(task_id)
        if task.state == "SUCCESS":
            return {"result": task.result}, 200
        if task.state == "FAILURE":
            return {"error": task.info}, 500
        return {"status": task.state}, 202

    def collect_osint_source(self, source_id: str):
        if self.send_task("collector_task", args=[source_id, True], queue="collectors"):
            logger.info(f"Collect for source {source_id} scheduled")
            return {"message": f"Refresh for source {source_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def preview_osint_source(self, source_id: str):
        task = self._celery.send_task("collector_preview", args=[source_id], queue="collectors", task_id=f"source_preview_{source_id}")
        logger.info(f"Collect for source {source_id} scheduled as {task.id}")
        return {"message": f"Refresh for source {source_id} scheduled", "task_id": task.id}, 200

    def collect_all_osint_sources(self):
        from core.model.osint_source import OSINTSource

        if self.error:
            return {"error": "Could not reach rabbitmq"}, 500
        sources = OSINTSource.get_all_for_collector()
        for source in sources:
            self.send_task("collector_task", args=[source.id, True], queue="collectors")
            logger.info(f"Collect for source {source.id} scheduled")
        return {"message": f"Refresh for source {len(sources)} scheduled"}, 200

    def push_to_connector(self, connector_id: str, story_ids: list[str]):
        if self.send_task("connector_task", args=[connector_id, story_ids], queue="connectors"):
            logger.info(f"Connector with id: {connector_id} scheduled")
            return {"message": f"Connector with id: {connector_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def pull_from_connector(self, connector_id: str):
        if self.send_task("connector_task", args=[connector_id, None], queue="connectors"):
            logger.info(f"Connector with id: {connector_id} scheduled")
            return {"message": f"Connector with id: {connector_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def gather_word_list(self, word_list_id: int):
        if self.send_task("gather_word_list", args=[word_list_id], queue="misc", task_id=f"gather_word_list_{word_list_id}"):
            logger.info(f"Gathering for WordList {word_list_id} scheduled")
            return {"message": f"Gathering for WordList {word_list_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def execute_bot_task(self, bot_id: int, filter: dict | None = None):
        bot_args: dict[str, int | dict] = {"bot_id": bot_id}
        if filter:
            bot_args["filter"] = filter
        if self.send_task("bot_task", kwargs=bot_args, queue="bots"):
            logger.info(f"Executing Bot {bot_id} scheduled")
            return {"message": f"Executing Bot {bot_id} scheduled", "id": bot_id}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def generate_product(self, product_id: str, countdown: int = 0):
        if self.send_task(
            "presenter_task", args=[product_id], queue="presenters", task_id=f"presenter_task_{product_id}", countdown=countdown
        ):
            logger.info(f"Generating Product {product_id} scheduled")
            return {"message": f"Generating Product {product_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def publish_product(self, product_id: str, publisher_id: str):
        if self.send_task("publisher_task", args=[product_id, publisher_id], queue="publishers", task_id=f"publisher_task_{product_id}"):
            logger.info(f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled")
            return {"message": f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled"}, 200
        return {"error": "Could not reach rabbitmq"}, 500

    def get_bot_signature(self, bot_id: str, source_id: str):
        return self._celery.signature("bot_task", kwargs={"bot_id": bot_id, "filter": {"SOURCE": source_id}}, queue="bots", immutable=True)

    def post_collection_bots(self, source_id: str):
        from core.model.bot import Bot

        post_collection_bots = list(Bot.get_post_collection())

        current_bot = self.get_bot_signature(post_collection_bots.pop(0), source_id)

        try:
            bot_chain = [self.get_bot_signature(bot_id, source_id) for bot_id in post_collection_bots]
            current_bot.apply_async(link=bot_chain, link_error=bot_chain, queue="bots", ignore_result=True)
            return {"message": f"Post collection bots scheduled for source {source_id}"}, 200
        except Exception as e:
            return {"error": "Could schedule post collection bots", "details": str(e)}, 500


def initialize(app: Flask, initial_setup: bool = True):
    global queue_manager
    queue_manager = QueueManager(app)
    try:
        with queue_manager._celery.connection() as conn:
            conn.ensure_connection(max_retries=3)
            queue_manager.error = ""
        if initial_setup:
            logger.info(f"QueueManager initialized: {queue_manager._celery.broker_connection().as_uri()}")
    except OperationalError:
        logger.error("Could not reach rabbitmq")
        queue_manager.error = "Could not reach rabbitmq"
    except Exception:
        logger.exception()
        queue_manager.error = "Could not reach rabbitmq"
