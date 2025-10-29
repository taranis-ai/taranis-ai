from __future__ import annotations

import asyncio
from typing import Any, cast

from flask import Flask
from prefect import get_client  # noqa: E402
from prefect.client.schemas.filters import FlowFilter, FlowFilterName
from prefect.client.schemas.objects import FlowRun
from prefect.deployments import run_deployment

from core.log import logger


queue_manager: "QueueManager | None" = None


class QueueManager:
    # Flow names used in the system
    FLOW_NAMES = [
        "collector-task-flow",
        "bot-task-flow",
        "presenter-task-flow",
        "publisher-task-flow",
        "connector-task-flow",
        "gather-word-list-flow",
    ]

    def __init__(self, app: Flask):
        self.app = app
        self.error: str = ""
        # No RabbitMQ dependencies - using Prefect directly
        self.queue_names = ["misc", "bots", "celery", "collectors", "presenters", "publishers", "connectors"]
        # Cache flow IDs to avoid repeated lookups
        self._flow_id_cache: dict[str, str] = {}
        # Try to pre-load flow IDs (best effort, may be empty if worker not started yet)
        self._load_flow_ids()

    def _load_flow_ids(self):
        """Load all flow IDs from Prefect API into cache (best effort, non-blocking)."""
        async def _fetch_flows():
            async with get_client() as client:
                # Fetch all flows at once
                flow_filter = FlowFilter(name=FlowFilterName(any_=self.FLOW_NAMES))
                flows = await client.read_flows(flow_filter=flow_filter)
                flow_map = {flow.name: flow.id for flow in flows}

                # Log if any expected flows are missing
                missing_flows = [name for name in self.FLOW_NAMES if name not in flow_map]
                if missing_flows:
                    logger.info(f"Flows not yet deployed (will lookup on demand): {missing_flows}")

                return flow_map

        try:
            self._flow_id_cache = asyncio.run(_fetch_flows())
            if self._flow_id_cache:
                logger.info(f"Pre-loaded {len(self._flow_id_cache)} flow IDs: {list(self._flow_id_cache.keys())}")
            else:
                logger.info("No flows pre-loaded. Will lookup flow IDs on demand when worker is available.")
        except Exception as e:
            logger.warning(f"Could not pre-load flows (worker may not be started): {e}")
            self.error = ""  # Don't set error - this is expected if worker isn't running yet

    def post_init(self):
        self.clear_queues()
        # Always try update - it will handle missing flows gracefully
        self.update_empty_word_lists()

    async def _get_flow_id_async(self, client, flow_name: str) -> str:
        """Get flow ID from cache, or lookup if not cached (async)."""
        # Check cache first
        if flow_name in self._flow_id_cache:
            return self._flow_id_cache[flow_name]

        # Not in cache - lookup from Prefect API
        logger.debug(f"Flow '{flow_name}' not in cache, looking up from Prefect...")
        flow_filter = FlowFilter(name=FlowFilterName(any_=[flow_name]))
        flows = await client.read_flows(flow_filter=flow_filter)
        if not flows:
            raise ValueError(f"Flow '{flow_name}' not found in Prefect. Is the worker running?")

        # Cache it for next time
        flow_id = flows[0].id
        self._flow_id_cache[flow_name] = flow_id
        logger.info(f"Cached flow ID for '{flow_name}'")
        return flow_id

    def _get_flow_id(self, flow_name: str) -> str:
        """Get flow ID from cache (synchronous lookup - only works if already cached)."""
        if flow_name not in self._flow_id_cache:
            raise ValueError(
                f"Flow '{flow_name}' not in cache. This should not happen - "
                f"use _get_flow_id_async() within async context instead."
            )
        return self._flow_id_cache[flow_name]

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

        if not word_lists:
            return []

        results: list[dict[str, Any]] = []
        for word_list in word_lists:
            try:
                request = WordListTaskRequest(word_list_id=word_list.id)
                flow_run = cast(
                    FlowRun,
                    run_deployment(
                        name="gather-word-list-flow/default",
                        parameters={"request": request.model_dump()},
                        timeout=0,
                    ),
                )
                logger.info(
                    f"[gather_word_list] Scheduled for WordList {word_list.id} (flow_run={flow_run.id})"
                )
                results.append({"word_list_id": word_list.id, "status": "ok", "result": str(flow_run.id)})
            except Exception as e:
                logger.exception(f"[gather_word_list] Failed for WordList {word_list.id}")
                results.append({"word_list_id": word_list.id, "status": "error", "error": str(e)})

        return results

    def get_queued_tasks(self):
        """
        Get running and pending flow runs from Prefect API for visibility in admin UI.
        """
        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        async def _get_flow_runs():
            async with get_client() as client:
                # Get recent flow runs in running/pending states
                flow_runs = await client.read_flow_runs(
                    limit=50,
                    sort="ID_DESC"  # Use valid sort option instead of CREATED_DESC
                )
                return flow_runs

        try:
            flow_runs = asyncio.run(_get_flow_runs())

            # Convert to format similar to RabbitMQ queues for compatibility
            tasks = []
            for run in flow_runs:
                if run.state_name in ['Pending', 'Running', 'Scheduled']:
                    tasks.append({
                        "name": run.flow_name or "unknown",
                        "messages": 1,  # Each flow run counts as 1 message
                        "flow_run_id": str(run.id),
                        "state": run.state_name,
                        "created": run.created.isoformat() if run.created else None
                    })

            logger.debug(f"Queued tasks from Prefect: {len(tasks)} active flow runs")
            return tasks, 200

        except Exception as e:
            logger.error(f"Could not reach Prefect API: {e}")
            return {"error": "Could not reach Prefect API"}, 500

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

        try:
            request = CollectorTaskRequest(source_id=source_id, preview=False)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="collector-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(f"[collector_task_flow] Scheduled collection for source {source_id} (flow_run={flow_run.id})")
            return {"message": f"Collection for source {source_id} scheduled", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"[collector_task_flow] Failed to schedule collection for source {source_id}")
            return {"error": f"Failed to schedule collection for source {source_id}", "details": str(e)}, 500

    def preview_osint_source(self, source_id: str):
        from models.prefect import CollectorTaskRequest

        try:
            request = CollectorTaskRequest(source_id=source_id, preview=True)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="collector-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(f"[collector_preview] Scheduled preview for source {source_id} (flow_run={flow_run.id})")
            return {"message": f"Preview executed for source {source_id}", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"[collector_preview] Failed to preview source {source_id}")
            return {"error": f"Failed to preview source {source_id}", "details": str(e)}, 500

    def collect_all_osint_sources(self):
        from core.model.osint_source import OSINTSource
        from models.prefect import CollectorTaskRequest

        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        sources = OSINTSource.get_all_for_collector()
        if not sources:
            return {"message": "No sources found"}, 200

        results: list[dict[str, Any]] = []
        for source in sources:
            try:
                request = CollectorTaskRequest(source_id=source.id, preview=False)
                flow_run = cast(
                    FlowRun,
                    run_deployment(
                        name="collector-task-flow/default",
                        parameters={"request": request.model_dump()},
                        timeout=0,
                    ),
                )
                logger.info(f"[collector_task_flow] Scheduled for {source.id} (flow_run={flow_run.id})")
                results.append({"source_id": source.id, "status": "ok", "result": str(flow_run.id)})
            except Exception as e:
                logger.exception(f"[collector_task_flow] Failed for {source.id}")
                results.append({"source_id": source.id, "status": "error", "error": str(e)})

        return {"message": f"Ran collector flow for {len(sources)} sources", "results": results}, 200

    def push_to_connector(self, connector_id: str, story_ids: list[str]):
        from models.prefect import ConnectorTaskRequest

        try:
            normalized_ids = list(story_ids) if story_ids else []
            request = ConnectorTaskRequest(connector_id=connector_id, story_ids=normalized_ids)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="connector-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(
                f"[connector_task] Push scheduled for connector_id={connector_id} (flow_run={flow_run.id})"
            )
            return {"message": "Connector push executed", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector push", "details": str(e)}, 500

    def pull_from_connector(self, connector_id: str):
        from models.prefect import ConnectorTaskRequest

        try:
            request = ConnectorTaskRequest(connector_id=connector_id, story_ids=None)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="connector-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(
                f"[connector_task] Pull scheduled for connector_id={connector_id} (flow_run={flow_run.id})"
            )
            return {"message": "Connector pull executed", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"Failed to run connector_task_flow for {connector_id}")
            return {"error": "Failed to schedule connector pull", "details": str(e)}, 500

    def gather_word_list(self, word_list_id: int):
        from models.prefect import WordListTaskRequest

        try:
            request = WordListTaskRequest(word_list_id=word_list_id)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="gather-word-list-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(
                f"Gathering for WordList {word_list_id} scheduled (flow_run={flow_run.id})"
            )
            return {"message": f"Gathering for WordList {word_list_id} completed", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"Failed to gather WordList {word_list_id}")
            return {"error": "Failed to gather WordList", "details": str(e)}, 500

    def execute_bot_task(self, bot_id: str, *, filter: dict[str, str] | None = None):
        from models.prefect import BotTaskRequest

        try:
            request = BotTaskRequest(bot_id=bot_id, filter=filter)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="bot-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(f"[bot_task] Scheduled bot {bot_id} (flow_run={flow_run.id})")
            return {
                "message": f"Executing Bot {bot_id} scheduled",
                "result": str(flow_run.id),
                "id": bot_id,
            }, 202
        except Exception as e:
            logger.exception(f"Failed to run bot_task_flow for {bot_id}")
            return {"error": f"Failed to schedule bot {bot_id}", "details": str(e)}, 500

    def generate_product(self, product_id: str, countdown: int = 0):
        from models.prefect import PresenterTaskRequest

        try:
            request = PresenterTaskRequest(product_id=product_id, countdown=countdown)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="presenter-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(f"[presenter_task] Product generation scheduled for {product_id}")
            return {"message": f"Product {product_id} generated", "result": str(flow_run.id)}, 200
        except Exception as e:
            logger.exception(f"Failed to run presenter_task_flow for {product_id}")
            return {"error": f"Failed to generate product {product_id}", "details": str(e)}, 500

    def publish_product(self, product_id: str, publisher_id: str):
        from models.prefect import PublisherTaskRequest

        try:
            request = PublisherTaskRequest(product_id=product_id, publisher_id=publisher_id)
            flow_run = cast(
                FlowRun,
                run_deployment(
                    name="publisher-task-flow/default",
                    parameters={"request": request.model_dump()},
                    timeout=0,
                ),
            )
            logger.info(
                f"[publisher_task] Publishing scheduled for {product_id} (flow_run={flow_run.id})"
            )
            return {"message": f"Product {product_id} published", "result": str(flow_run.id)}, 200
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

        results: list[dict[str, Any]] = []
        for bot_id in post_collection_bots:
            try:
                request = BotTaskRequest(bot_id=str(bot_id), filter={"SOURCE": source_id})
                flow_run = cast(
                    FlowRun,
                    run_deployment(
                        name="bot-task-flow/default",
                        parameters={"request": request.model_dump()},
                        timeout=0,
                    ),
                )
                results.append({"bot_id": bot_id, "result": str(flow_run.id)})
            except Exception as e:
                logger.exception(f"Failed to run bot {bot_id} for source {source_id}")
                results.append({"bot_id": bot_id, "error": str(e)})

        return {
            "message": f"Scheduled {len(post_collection_bots)} post-collection bots",
            "results": results,
        }, 200


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
