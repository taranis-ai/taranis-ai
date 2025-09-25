from __future__ import annotations

import asyncio
from typing import Any

from flask import Flask
import requests
from requests.auth import HTTPBasicAuth
from prefect import get_client  # noqa: E402

from core.log import logger


queue_manager: "QueueManager | None" = None


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
        self.update_empty_word_lists()

    def clear_queues(self):
        # With Prefect, we don't push to broker queues anymore; keep this as a no-op/log
        logger.info("All queues cleared")

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
        from models.prefect import WordListTaskRequest

        if self.error:
            return

        word_lists = WordList.get_all_empty() or []
        
        async def _run_word_list_updates():
            async with get_client() as client:
                results: list[dict[str, Any]] = []
                for word_list in word_lists:
                    try:
                        request = WordListTaskRequest(word_list_id=word_list.id)
                        flow_run = await client.create_flow_run(
                            flow_name="gather-word-list-flow",
                            parameters={"request": request.dict()}
                        )
                        logger.info(f"[gather_word_list] Ran for WordList {word_list.id}")
                        results.append({"word_list_id": word_list.id, "status": "ok", "result": flow_run.id})
                    except Exception as e:
                        logger.exception(f"[gather_word_list] Failed for WordList {word_list.id}")
                        results.append({"word_list_id": word_list.id, "status": "error", "error": str(e)})
                return results

        try:
            return asyncio.run(_run_word_list_updates())
        except Exception as e:
            logger.exception("Failed to update empty word lists")
            return []

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
        from models.prefect import CollectorTaskRequest

        async def _run_collector():
            async with get_client() as client:
                request = CollectorTaskRequest(source_id=source_id, preview=False)
                flow_run = await client.create_flow_run(
                    flow_name="collector-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_collector())
            return {"message": f"Collection for source {source_id} scheduled", "result": result}, 200
        except Exception as e:
            return {"error": f"Failed to schedule collection for source {source_id}", "details": str(e)}, 500

    def preview_osint_source(self, source_id: str):
        from models.prefect import CollectorTaskRequest

        async def _run_preview():
            async with get_client() as client:
                request = CollectorTaskRequest(source_id=source_id, preview=True)
                flow_run = await client.create_flow_run(
                    flow_name="collector-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_preview())
            logger.info(f"[collector_preview] Ran for source {source_id}, result: {result}")
            return {"message": f"Preview executed for source {source_id}", "result": result}, 200
        except Exception as e:
            return {"error": f"Failed to preview source {source_id}", "details": str(e)}, 500

    def collect_all_osint_sources(self):
        from core.model.osint_source import OSINTSource
        from models.prefect import CollectorTaskRequest

        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        sources = OSINTSource.get_all_for_collector()
        if not sources:
            return {"message": "No sources found"}, 200

        async def _run_all_collectors():
            async with get_client() as client:
                results: list[dict[str, Any]] = []
                for source in sources:
                    try:
                        request = CollectorTaskRequest(source_id=source.id, preview=False)
                        flow_run = await client.create_flow_run(
                            flow_name="collector-task-flow",
                            parameters={"request": request.dict()}
                        )
                        logger.info(f"[collector_task_flow] Ran for {source.id}")
                        results.append({"source_id": source.id, "status": "ok", "result": flow_run.id})
                    except Exception as e:
                        logger.exception(f"[collector_task_flow] Failed for {source.id}")
                        results.append({"source_id": source.id, "status": "error", "error": str(e)})
                return results

        try:
            results = asyncio.run(_run_all_collectors())
            return {"message": f"Ran collector flow for {len(sources)} sources", "results": results}, 200
        except Exception as e:
            return {"error": f"Failed to schedule collector flows", "details": str(e)}, 500

    def push_to_connector(self, connector_id: str, story_ids: list[str]):
        from models.prefect import ConnectorTaskRequest

        async def _run_connector_push():
            async with get_client() as client:
                normalized_ids = list(story_ids) if story_ids else []
                request = ConnectorTaskRequest(connector_id=connector_id, story_ids=normalized_ids)
                flow_run = await client.create_flow_run(
                    flow_name="connector-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_connector_push())
            logger.info(f"[connector_task] Push scheduled for connector_id={connector_id}")
            return {"message": "Connector push executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector push", "details": str(e)}, 500

    def pull_from_connector(self, connector_id: str):
        from models.prefect import ConnectorTaskRequest

        async def _run_connector_pull():
            async with get_client() as client:
                request = ConnectorTaskRequest(connector_id=connector_id, story_ids=None)
                flow_run = await client.create_flow_run(
                    flow_name="connector-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_connector_pull())
            logger.info(f"[connector_task] Pull scheduled for connector_id={connector_id}")
            return {"message": "Connector pull executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector pull", "details": str(e)}, 500

    def gather_word_list(self, word_list_id: int):
        from models.prefect import WordListTaskRequest

        async def _run_word_list():
            async with get_client() as client:
                request = WordListTaskRequest(word_list_id=word_list_id)
                flow_run = await client.create_flow_run(
                    flow_name="gather-word-list-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_word_list())
            logger.info(f"Gathering for WordList {word_list_id} scheduled with result: {result}")
            return {"message": f"Gathering for WordList {word_list_id} completed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to gather WordList {word_list_id}")
            return {"error": "Failed to gather WordList", "details": str(e)}, 500

    def execute_bot_task(self, bot_id: int, filter: dict | None = None):
        from models.prefect import BotTaskRequest

        async def _run_bot_task():
            async with get_client() as client:
                request = BotTaskRequest(bot_id=str(bot_id), filter=filter)
                flow_run = await client.create_flow_run(
                    flow_name="bot-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_bot_task())
            logger.info(f"[bot_task] Executed for bot_id={bot_id}, result: {result}")
            return {"message": f"Bot {bot_id} executed", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run bot_task_flow for {bot_id}")
            return {"error": f"Failed to execute bot {bot_id}", "details": str(e)}, 500

    def generate_product(self, product_id: str, countdown: int = 0):
        from models.prefect import PresenterTaskRequest

        async def _run_presenter_task():
            async with get_client() as client:
                request = PresenterTaskRequest(product_id=product_id, countdown=countdown)
                flow_run = await client.create_flow_run(
                    flow_name="presenter-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_presenter_task())
            logger.info(f"[presenter_task] Product generation scheduled for {product_id}")
            return {"message": f"Product {product_id} generated", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run presenter_task_flow for {product_id}")
            return {"error": f"Failed to generate product {product_id}", "details": str(e)}, 500

    def publish_product(self, product_id: str, publisher_id: str):
        from models.prefect import PublisherTaskRequest

        async def _run_publisher_task():
            async with get_client() as client:
                request = PublisherTaskRequest(product_id=product_id, publisher_id=publisher_id)
                flow_run = await client.create_flow_run(
                    flow_name="publisher-task-flow",
                    parameters={"request": request.dict()}
                )
                return flow_run.id

        try:
            result = asyncio.run(_run_publisher_task())
            logger.info(f"[publisher_task] Publishing scheduled for {product_id}")
            return {"message": f"Product {product_id} published", "result": result}, 200
        except Exception as e:
            logger.exception(f"Failed to run publisher_task_flow for {product_id}")
            return {"error": f"Failed to publish product {product_id}", "details": str(e)}, 500
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
        from models.prefect import BotTaskRequest

        post_collection_bots = list(Bot.get_post_collection())
        if not post_collection_bots:
            return {"message": "No post collection bots found"}, 200

        async def _run_post_collection_bots():
            async with get_client() as client:
                results: list[dict[str, Any]] = []
                for bot_id in post_collection_bots:
                    try:
                        request = BotTaskRequest(bot_id=str(bot_id), filter={"SOURCE": source_id})
                        flow_run = await client.create_flow_run(
                            flow_name="bot-task-flow",
                            parameters={"request": request.dict()}
                        )
                        results.append({"bot_id": bot_id, "result": flow_run.id})
                    except Exception as e:
                        logger.exception(f"Failed to run bot {bot_id} for source {source_id}")
                        results.append({"bot_id": bot_id, "error": str(e)})
                return results

        try:
            results = asyncio.run(_run_post_collection_bots())
            return {"message": f"Scheduled {len(post_collection_bots)} post-collection bots", "results": results}, 200
        except Exception as e:
            return {"error": "Failed to schedule post-collection bots", "details": str(e)}, 500

        return {"message": f"Post collection bots scheduled for source {source_id}", "results": results}, 200


def initialize(app: Flask, initial_setup: bool = True):
    """
    Initialize QueueManager against Prefect; run baseline setup if requested.
    """
    global queue_manager
    queue_manager = QueueManager(app)

    try:

        async def _test_connection():
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
