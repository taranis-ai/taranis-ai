from __future__ import annotations

import asyncio
from typing import Any

from flask import Flask
import requests
from requests.auth import HTTPBasicAuth
from prefect import get_client

from core.log import logger


queue_manager: "QueueManager"


class QueueManager:
    def __init__(self, app: Flask):
        self.app = app
        self.error: str = ""
        self.mgmt_api = f"http://{app.config['QUEUE_BROKER_HOST']}:15672/api/"
        self.queue_user = app.config["QUEUE_BROKER_USER"]
        self.queue_password = app.config["QUEUE_BROKER_PASSWORD"]
        # Kept for compatibility with existing dashboards; not used by Prefect execution path
        self.queue_names = ["misc", "bots", "celery", "collectors", "presenters", "publishers", "connectors"]


    def post_init(self):
        self.clear_queues()
        self.update_task_queue_from_osint_sources()
        self.update_empty_word_lists()

    def clear_queues(self):
        # With Prefect, we don't push to broker queues anymore; keep this as a no-op/log
        logger.info("All queues cleared")

    def update_task_queue_from_osint_sources(self):
        """
        Re-populate collector runs for available sources via Prefect flows.
        """
        from core.model.osint_source import OSINTSource
        from models.collector import CollectorTaskRequest
        from worker.flows.collector_task_flow import collector_task_flow


        sources = OSINTSource.get_all_for_collector()
        for source in sources:
            request = CollectorTaskRequest(source_id=source.id, preview=False)
            collector_task_flow(request)
        logger.info(f"Updated task queue from {len(sources)} osint sources")

    async def list_worker_queues(self, limit: int = 10):
        """
        For smoke/ping purposes: fetch a small page of flow runs from Prefect.
        """
        async with get_client() as client:
            try:
                return await client.read_flow_runs(limit=limit)
            except TypeError:
                runs = await client.read_flow_runs()
                return runs[:limit]

    def update_empty_word_lists(self):
        """
        Run the (Prefect) gather_word_list flow for empty lists, collect results,
        and return a structured per-list outcome.
        """
        from core.model.word_list import WordList
        from worker.flows.gather_word_list_flow import gather_word_list_flow

        if self.error:
            return

        word_lists = WordList.get_all_empty() or []
        results: list[dict[str, Any]] = []
        for word_list in word_lists:
            try:
                result = gather_word_list_flow(word_list.id)
                logger.info(f"[gather_word_list] Ran for WordList {word_list.id}")
                results.append({"word_list_id": word_list.id, "status": "ok", "result": result})
            except Exception as e:
                logger.exception(f"[gather_word_list] Failed for WordList {word_list.id}")
                results.append({"word_list_id": word_list.id, "status": "error", "error": str(e)})

        return results

    def get_queued_tasks(self):
        """
        Still calls RabbitMQ API for visibility in admin UI; does not drive Prefect.
        """
        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        response = requests.get(
            f"{self.mgmt_api}queues/",
            auth=HTTPBasicAuth(self.queue_user, self.queue_password),
            timeout=5,
        )
        if not response.ok:
            logger.error(response.text)
            return {"error": "Could not reach rabbitmq"}, 500

        tasks = [{key: d[key] for key in ("messages", "name") if key in d} for d in response.json()]
        logger.debug(f"Queued tasks: {tasks}")
        return tasks, 200

    def ping_workers(self):
        """
        Ping Prefect orchestration by listing flow runs.
        """
        if self.error:
            logger.error("QueueManager not initialized")
            return {"error": "QueueManager not initialized"}, 500
        try:
            return asyncio.run(self.list_worker_queues())
        except Exception:
            self.error = "Could not reach prefect"
            return {"error": "Could not reach prefect"}, 500

    def get_queue_status(self) -> tuple[dict, int]:
        """
        Health-check against Prefect.
        """
        try:
            async def _ping():
                from prefect.client.orchestration import get_client
                async with get_client() as client:
                    await client.read_flow_runs(limit=1)
                return True

            asyncio.run(_ping())
            return {"status": "Prefect agent reachable"}, 200

        except Exception as e:
            return {"error": "Prefect not available", "details": str(e)}, 500


    def get_task(self, task_id) -> tuple[dict, int]:
        return {"error": "Method not supported in Prefect - use flow run ID instead"}, 501


    def collect_osint_source(self, source_id: str):
        from models.collector import CollectorTaskRequest
        from worker.flows.collector_task_flow import collector_task_flow

        request = CollectorTaskRequest(source_id=source_id, preview=False)
        result = collector_task_flow(request)
        return {"message": f"Collection for source {source_id} scheduled", "result": result}, 200

    def preview_osint_source(self, source_id: str):
        from models.collector import CollectorTaskRequest
        from worker.flows.collector_task_flow import collector_task_flow

        try:
            request = CollectorTaskRequest(source_id=source_id, preview=True)
            result = collector_task_flow(request)
            logger.info(f"[collector_preview] Ran for source {source_id}, result: {result}")
            return {"message": f"Preview executed for source {source_id}", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run collector_preview for {source_id}")
            return {"error": f"Failed to preview source {source_id}", "details": str(e)}, 500

    def collect_all_osint_sources(self):
        from core.model.osint_source import OSINTSource
        from models.collector import CollectorTaskRequest
        from worker.flows.collector_task_flow import collector_task_flow

        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        sources = OSINTSource.get_all_for_collector()
        if not sources:
            return {"message": "No sources found"}, 200

        results: list[dict[str, Any]] = []
        for source in sources:
            try:
                request = CollectorTaskRequest(source_id=source.id, preview=False)
                result = collector_task_flow(request)
                logger.info(f"[collector_task_flow] Ran for {source.id}")
                results.append({"source_id": source.id, "status": "ok", "result": result})
            except Exception as e:
                logger.exception(f"[collector_task_flow] Failed for {source.id}")
                results.append({"source_id": source.id, "status": "error", "error": str(e)})

        return {"message": f"Ran collector flow for {len(sources)} sources", "results": results}, 200

    def push_to_connector(self, connector_id: str, story_ids: list[str]):
        from models.connector import ConnectorTaskRequest
        from worker.flows.connector_task_flow import connector_task_flow

        try:
            normalized_ids = list(story_ids) if story_ids else []
            request = ConnectorTaskRequest(connector_id=connector_id, story_ids=normalized_ids)
            result = connector_task_flow(request)
            logger.info(f"[connector_task] Push scheduled for connector_id={connector_id}")
            return {"message": "Connector push executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector push", "details": str(e)}, 500

    def pull_from_connector(self, connector_id: str):
        from models.connector import ConnectorTaskRequest
        from worker.flows.connector_task_flow import connector_task_flow

        try:
            request = ConnectorTaskRequest(connector_id=connector_id, story_ids=None)
            result = connector_task_flow(request)
            logger.info(f"[connector_task] Pull scheduled for connector_id={connector_id}")
            return {"message": "Connector pull executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector pull", "details": str(e)}, 500

    def gather_word_list(self, word_list_id: int):
        from worker.flows.gather_word_list_flow import gather_word_list_flow

        try:
            result = gather_word_list_flow(word_list_id)
            logger.info(f"Gathering for WordList {word_list_id} scheduled with result: {result}")
            return {"message": f"Gathering for WordList {word_list_id} completed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to gather WordList {word_list_id}")
            return {"error": "Failed to gather WordList", "details": str(e)}, 500

    def execute_bot_task(self, bot_id: int, filter: dict | None = None):
        from models.bot import BotTaskRequest
        from worker.flows.bot_task_flow import bot_task_flow

        try:
            request = BotTaskRequest(bot_id=bot_id, filter=filter)
            result = bot_task_flow(request)
            logger.info(f"[bot_task] Executed for bot_id={bot_id}, result: {result}")
            return {"message": f"Bot {bot_id} executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run bot_task_flow for {bot_id}")
            return {"error": f"Failed to execute bot {bot_id}", "details": str(e)}, 500

    def generate_product(self, product_id: str, countdown: int = 0):
        from models.presenter import PresenterTaskRequest
        from worker.flows.presenter_task_flow import presenter_task_flow

        try:
            request = PresenterTaskRequest(product_id=product_id, countdown=countdown)
            result = presenter_task_flow(request)
            logger.info(f"[presenter_task] Product generation scheduled for {product_id}")
            return {"message": f"Product {product_id} generated", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run presenter_task_flow for {product_id}")
            return {"error": f"Failed to generate product {product_id}", "details": str(e)}, 500

    def publish_product(self, product_id: str, publisher_id: str):
        from models.publisher import PublisherTaskRequest
        from worker.flows.publisher_task_flow import publisher_task_flow

        try:
            request = PublisherTaskRequest(product_id=product_id, publisher_id=publisher_id)
            result = publisher_task_flow(request)
            logger.info(f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled")
            return {
                "message": f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled",
                "result": result,
            }, 200
        except Exception as e:
            logger.exception(f"Failed to run publisher_task_flow for {product_id}")
            return {"error": f"Failed to publish product {product_id}", "details": str(e)}, 500

    def get_bot_signature(self, bot_id: str, source_id: str):
        """
        Kept for backward compatibility. With Prefect, we directly trigger flows;
        still return a predictable shape for consumers that expect a 'signature-like' dict.
        """
        return {"bot_id": bot_id, "filter": {"SOURCE": source_id}}

    def post_collection_bots(self, source_id: str):
        from core.model.bot import Bot
        from models.bot import BotTaskRequest
        from worker.flows.bot_task_flow import bot_task_flow

        post_collection_bots = list(Bot.get_post_collection())
        if not post_collection_bots:
            return {"message": "No post collection bots found"}, 200

        results: list[dict[str, Any]] = []
        for bot_id in post_collection_bots:
            try:
                request = BotTaskRequest(bot_id=bot_id, filter={"SOURCE": source_id})
                result = bot_task_flow(request)
                results.append({"bot_id": bot_id, "result": result})
            except Exception as e:
                logger.exception(f"Failed to run bot {bot_id} for source {source_id}")
                results.append({"bot_id": bot_id, "error": str(e)})

        return {"message": f"Post collection bots scheduled for source {source_id}", "results": results}, 200


def initialize(app: Flask, initial_setup: bool = True):
    """
    Initialize QueueManager against Prefect; run baseline setup if requested.
    """
    global queue_manager
    queue_manager = QueueManager(app)

    try:
        async def _test_connection():
            from prefect.client.orchestration import get_client
            async with get_client() as client:
                await client.read_flow_runs(limit=1)

        asyncio.run(_test_connection())
        queue_manager.error = ""

        if initial_setup:
            logger.info("QueueManager initialized with Prefect")
            queue_manager.post_init()

    except Exception as e:
        logger.error(f"Could not initialize QueueManager: {e}")
        queue_manager.error = "Could not connect to Prefect"
