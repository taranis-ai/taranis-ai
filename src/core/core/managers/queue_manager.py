"""Queue Manager for RQ (Redis Queue) task management

This module manages job queues and task scheduling using RQ and Redis.

Architecture:
------------
1. Core Application (this module):
   - Manages RQ queues (collectors, bots, presenters, publishers, etc.)
   - Enqueues immediate tasks via enqueue_task()
   - Stores cron definitions in Redis (`rq:cron:def`)

2. Cron Scheduler (separate worker process):
   - Runs as `taranis-cron`
   - Polls Redis for cron definitions (`rq:cron:def`)
   - Tracks next run timestamps in `rq:cron:next`
   - Uses leader lock `rq:cron:leader` for single active scheduler

3. RQ Workers:
   - Pick up enqueued jobs from queues
   - Execute task functions (collectors, bots, etc.)
   - No self-rescheduling logic needed

Schedule Updates:
----------------
When a source/bot schedule is updated:
1. Changes are saved to the database
2. Core upserts/deletes the job definition in `rq:cron:def`
3. The scheduler process picks up changes on its next poll cycle
"""

import contextlib
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from croniter import CroniterBadCronError, CroniterBadDateError, croniter
from flask import Flask
from models.admin import CronSpec
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from core.config import Config
from core.log import logger
from core.service.simple_web_collector import get_simple_web_collector_url


OVERDUE_GRACE_PERIOD = timedelta(minutes=5)
CRON_DEFS_KEY = "rq:cron:def"
CRON_EVENTS_KEY = "rq:cron:events"
CRON_NEXT_KEY = "rq:cron:next"
TOKEN_CLEANUP_JOB_ID = "cleanup_token_blacklist"
TOKEN_CLEANUP_CRON = "0 2 * * *"
TOKEN_CLEANUP_DISPLAY_NAME = "Maintenance: Cleanup Token Blacklist"


def _decode_redis_value(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, seconds = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m" if seconds == 0 else f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h" if minutes == 0 else f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d" if hours == 0 else f"{days}d {hours}h"


def _format_relative_time(target: datetime | None, reference: datetime) -> str | None:
    if not target:
        return None
    delta = target - reference
    seconds = int(delta.total_seconds())
    if seconds == 0:
        return "now"
    label = _format_duration(abs(delta))
    return f"in {label}" if seconds > 0 else f"{label} ago"


def _as_naive_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _format_utc_timestamp(value: datetime | None) -> str | None:
    normalized = _as_naive_utc(value)
    if not normalized:
        return None
    return f"{normalized.strftime('%Y-%m-%d %H:%M:%S')} UTC"


def _cron_run_missed_since_last_run(job: dict[str, Any], now: datetime, last_run_dt: datetime | None) -> bool:
    schedule = job.get("schedule")
    if not schedule or last_run_dt is None:
        return False

    try:
        next_expected_run = croniter(schedule, last_run_dt).get_next(datetime)
    except (CroniterBadCronError, CroniterBadDateError):
        return False

    return now > (next_expected_run + OVERDUE_GRACE_PERIOD)


def _annotate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for job in jobs:
        last_run_dt = _as_naive_utc(job.get("last_run"))
        next_run_dt = _as_naive_utc(job.get("next_run_time"))
        prev_run_dt = _as_naive_utc(job.get("previous_run_time"))

        job["last_run"] = last_run_dt
        job["next_run_time"] = next_run_dt
        job["previous_run_time"] = prev_run_dt

        job["last_run_display"] = _format_utc_timestamp(last_run_dt)
        job["last_run_relative"] = f"{_format_duration(now - last_run_dt)} ago" if last_run_dt else None
        job["next_run_display"] = _format_utc_timestamp(next_run_dt)
        job["next_run_relative"] = _format_relative_time(next_run_dt, now)

        variant = "ghost"
        label = "Queued" if job.get("type") == "scheduled" else "Pending"
        is_overdue = False

        if job.get("type") == "cron":
            if not last_run_dt:
                label = "Pending first run"
                job["status_badge"] = {"variant": variant, "label": label}
                job["is_overdue"] = False
                continue
            elif _cron_run_missed_since_last_run(job, now, last_run_dt):
                label = "Missed"
                variant = "error"
                is_overdue = True
            elif prev_run_dt and last_run_dt >= prev_run_dt or not prev_run_dt:
                label = "On schedule"
                variant = "success"
            if prev_run_dt:
                overdue_threshold = prev_run_dt + OVERDUE_GRACE_PERIOD
                ran_current_window = bool(last_run_dt and last_run_dt >= prev_run_dt)
                if now > overdue_threshold and not ran_current_window:
                    label = "Missed"
                    variant = "error"
                    is_overdue = True
                elif ran_current_window:
                    label = "On schedule"
                    variant = "success"

        elif next_run_dt and now > (next_run_dt + OVERDUE_GRACE_PERIOD):
            label = "Missed"
            variant = "warning"
            is_overdue = True

        job["status_badge"] = {"variant": variant, "label": label}
        job["is_overdue"] = is_overdue

    return jobs


def _compute_next_timestamp(cron: str | None, interval: int | None, base_ts: float) -> float:
    if cron:
        dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
        return croniter(cron, dt).get_next(datetime).timestamp()
    if interval is not None:
        return base_ts + int(interval)
    raise ValueError("CronSpec must provide either cron or interval")


queue_manager: "QueueManager"

# Task name to full module path mapping
TASK_MAP = {
    "collector_task": "worker.collectors.collector_tasks.collector_task",
    "collector_preview": "worker.collectors.collector_tasks.collector_preview",
    "bot_task": "worker.bots.bot_tasks.bot_task",
    "presenter_task": "worker.presenters.presenter_tasks.presenter_task",
    "publisher_task": "worker.publishers.publisher_tasks.publisher_task",
    "connector_task": "worker.connectors.connector_tasks.connector_task",
    "gather_word_list": "worker.misc.misc_tasks.gather_word_list",
    "cleanup_token_blacklist": "worker.misc.misc_tasks.cleanup_token_blacklist",
    "fetch_single_news_item": "worker.collectors.collector_tasks.fetch_single_news_item",
}


class QueueManager:
    def __init__(self, app: Flask):
        self._redis: Redis | None = None
        self._queues: dict[str, Queue] = {}
        self.error: str = ""
        self.redis_url = Config.REDIS_URL
        self.redis_password: str | None = None
        self.queue_names = ["misc", "bots", "collectors", "presenters", "publishers", "connectors"]
        if redis_password_value := Config.REDIS_PASSWORD:
            if secret := redis_password_value.get_secret_value():
                self.redis_password = secret

        try:
            self.init_app(app)
        except Exception as e:
            logger.error(f"Failed to initialize QueueManager: {e}")
            self.error = f"Could not connect to Redis: {e}"

    def init_app(self, app: Flask):
        """Initialize Redis connection and create queues"""
        self._redis = Redis.from_url(
            self.redis_url,
            password=self.redis_password,
            decode_responses=False,
        )

        # Test connection
        self._redis.ping()

        # Create queue instances
        for queue_name in self.queue_names:
            self._queues[queue_name] = Queue(queue_name, connection=self._redis)

        app.extensions["rq"] = self
        logger.info(f"QueueManager initialized with Redis: {self.redis_url}")

    def post_init(self):
        """Post-initialization tasks"""
        self.clear_queues()
        self.reschedule_all()
        self.update_empty_word_lists()

    def reschedule_all(self):
        """Reconcile Redis cron definitions with the currently enabled sources and bots."""
        if self.error:
            return
        try:
            managed_specs = self._get_managed_cron_specs()
            desired_ids = set(managed_specs)
            current_ids = self._get_registered_cron_job_ids()
            housekeeping_ids = set(self._get_housekeeping_cron_specs())
            managed_current_ids = {
                job_id for job_id in current_ids if job_id.startswith(("osint_source_", "bot_")) or job_id in housekeeping_ids
            }
            stale_ids = sorted(managed_current_ids - desired_ids)

            registered = 0
            source_count = 0
            bot_count = 0
            for job_id, spec in managed_specs.items():
                if self.register_cron_job(spec):
                    registered += 1

                if job_id.startswith("osint_source_"):
                    source_count += 1
                elif job_id.startswith("bot_"):
                    bot_count += 1

            purged_jobs = 0
            purged_tasks = 0
            if stale_ids:
                for stale_id in stale_ids:
                    self.unregister_cron_job(stale_id)
                purged_jobs, purged_tasks = self.purge_job_artifacts(prefixes=[f"cron_{job_id}_" for job_id in stale_ids])

            logger.info(
                "Synchronized %s source cron jobs and %s bot cron jobs, removed %s stale registrations, "
                "purged %s stale Redis jobs and %s task rows.",
                source_count,
                bot_count,
                len(stale_ids),
                purged_jobs,
                purged_tasks,
            )
            logger.debug("Registered %s managed cron definitions", registered)
        except Exception as e:
            logger.error(f"Failed to check sources and bots: {e}")

    def _get_managed_cron_specs(self) -> dict[str, CronSpec]:
        from core.model.bot import Bot
        from core.model.osint_source import OSINTSource

        specs: dict[str, CronSpec] = {}

        for source in OSINTSource.get_all_for_collector():
            if not getattr(source, "enabled", True):
                continue
            if not source.get_schedule_with_default():
                continue
            spec = source.get_cron_spec()
            specs[spec.job_id] = spec

        for bot in Bot.get_all_for_collector():
            if not getattr(bot, "enabled", True):
                continue
            if not bot.get_schedule():
                continue
            spec = bot.get_cron_spec()
            specs[spec.job_id] = spec

        specs |= self._get_housekeeping_cron_specs()
        return specs

    @staticmethod
    def _get_housekeeping_cron_specs() -> dict[str, CronSpec]:
        spec = CronSpec(
            meta={"name": TOKEN_CLEANUP_DISPLAY_NAME},
            job_id=TOKEN_CLEANUP_JOB_ID,
            cron=TOKEN_CLEANUP_CRON,
            func_path="cleanup_token_blacklist",
            queue_name="misc",
        )
        return {spec.job_id: spec}

    def _get_registered_cron_job_ids(self) -> set[str]:
        if self.error or not self._redis:
            return set()

        try:
            raw_ids = self._redis.hkeys(CRON_DEFS_KEY)
        except Exception:
            return set()

        return {_decode_redis_value(raw_id) for raw_id in raw_ids}

    def purge_job_artifacts(
        self,
        *,
        exact_ids: set[str] | None = None,
        prefixes: list[str] | None = None,
    ) -> tuple[int, int]:
        exact_ids = exact_ids or set()
        prefixes = prefixes or []
        if not exact_ids and not prefixes:
            return 0, 0

        return self._purge_rq_jobs(exact_ids=exact_ids, prefixes=prefixes), self._purge_task_rows(
            exact_ids=exact_ids,
            prefixes=prefixes,
        )

    def _purge_rq_jobs(self, *, exact_ids: set[str], prefixes: list[str]) -> int:
        if self.error or not self._redis:
            return 0

        import rq.registry as rq_registry

        def matches(job_id: str) -> bool:
            return job_id in exact_ids or any(job_id.startswith(prefix) for prefix in prefixes)

        removed_ids: set[str] = set()

        for queue in self._queues.values():
            queued_ids: list[str] = []
            with contextlib.suppress(Exception):
                if hasattr(queue, "get_job_ids"):
                    queued_ids = list(queue.get_job_ids())
                elif callable(getattr(queue, "job_ids", None)):
                    queued_ids = list(queue.job_ids())
                elif getattr(queue, "job_ids", None) is not None:
                    queued_ids = list(queue.job_ids)

            for job_id in queued_ids:
                if not matches(job_id) or job_id in removed_ids:
                    continue
                with contextlib.suppress(Exception):
                    job = Job.fetch(job_id, connection=self._redis)
                    job.cancel()
                    job.delete()
                    removed_ids.add(job_id)

            registry_classes = [rq_registry.FailedJobRegistry, rq_registry.ScheduledJobRegistry]
            deferred_registry = getattr(rq_registry, "DeferredJobRegistry", None)
            if deferred_registry is not None:
                registry_classes.append(deferred_registry)

            for registry_cls in registry_classes:
                with contextlib.suppress(Exception):
                    registry = registry_cls(queue=queue)
                    for job_id in list(registry.get_job_ids()):
                        if not matches(job_id) or job_id in removed_ids:
                            continue
                        try:
                            registry.remove(job_id, delete_job=True)
                        except TypeError:
                            registry.remove(job_id)
                            with contextlib.suppress(Exception):
                                Job.fetch(job_id, connection=self._redis).delete()
                        removed_ids.add(job_id)

        return len(removed_ids)

    def _purge_task_rows(self, *, exact_ids: set[str], prefixes: list[str]) -> int:
        from sqlalchemy import or_

        from core.managers.db_manager import db
        from core.model.task import Task as TaskModel

        conditions = [TaskModel.id.in_(exact_ids)] if exact_ids else []
        conditions.extend(TaskModel.id.like(f"{prefix}%") for prefix in prefixes)
        if not conditions:
            return 0

        tasks = list(db.session.execute(db.select(TaskModel).where(or_(*conditions))).scalars())
        if not tasks:
            return 0

        for task in tasks:
            db.session.delete(task)
        db.session.commit()
        return len(tasks)

    def clear_queues(self):
        """Clear all queues on startup"""
        if self.error:
            return
        try:
            for queue_name, queue in self._queues.items():
                queue.empty()
            logger.info("All queues cleared")
        except Exception as e:
            logger.error(f"Failed to clear queues: {e}")

    def publish_schedule_cache_invalidation(self) -> int:
        from core.service.cache_invalidation import cache_invalidation_service

        return cache_invalidation_service.invalidate_scope("schedule")

    @property
    def redis(self) -> Redis | None:
        return self._redis

    def get_queue(self, queue_name: str) -> Queue | None:
        """Get a queue by name"""
        return self._queues.get(queue_name)

    def update_empty_word_lists(self):
        """Gather word lists that have no entries"""
        from core.model.word_list import WordList

        if self.error:
            return

        word_lists = WordList.get_all_empty() or []
        for word_list in word_lists:
            logger.debug(f"Gathering word_list {word_list.id}")
            self.enqueue_task("misc", "gather_word_list", word_list.id, job_id=f"gather_word_list_{word_list.id}")
        logger.info(f"Gathering for {len(word_lists)} empty WordLists scheduled")

    def gather_all_word_lists(self):
        """Gather all word lists"""
        from core.model.word_list import WordList

        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        word_lists = WordList.get_all_for_collector() or []
        for word_list in word_lists:
            self.enqueue_task("misc", "gather_word_list", word_list.id, job_id=f"gather_word_list_{word_list.id}")
        return {"message": "Gathering for all WordLists scheduled"}, 200

    def get_queued_tasks(self):
        """Get queued tasks from all queues"""
        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        try:
            tasks = [{"name": queue_name, "messages": len(queue)} for queue_name, queue in self._queues.items()]
            logger.debug(f"Queued tasks: {tasks}")
            return tasks, 200
        except Exception as e:
            logger.error(f"Failed to get queued tasks: {e}")
            return {"error": "Could not reach Redis"}, 500

    def ping_workers(self):
        """Check worker status"""
        if self.error:
            logger.error("QueueManager not initialized")
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.worker import Worker

            workers = Worker.all(connection=self._redis)
            self.error = ""
            return [
                {
                    "name": worker.name,
                    "status": "ok" if worker.state in ("busy", "idle") else worker.state,
                }
                for worker in workers
            ]
        except Exception as e:
            logger.error(f"Failed to ping workers: {e}")
            self.error = "Could not reach Redis"
            return {"error": "Could not reach Redis"}, 500

    def enqueue_task(self, queue_name: str, task_name: str, *args, job_id: str | None = None, **kwargs):
        """Enqueue a task immediately"""
        if self.error:
            return False

        try:
            queue = self.get_queue(queue_name)
            if not queue:
                logger.error(f"Queue {queue_name} not found")
                return False

            task_func = TASK_MAP.get(task_name)
            if not task_func:
                logger.error(f"Unknown task: {task_name}")
                return False

            return queue.enqueue(task_func, *args, job_id=job_id, **kwargs)
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_name}: {e}")
            return False

    def _await_job_result(self, job: Job, timeout: float = 60.0, poll_interval: float = 0.2):
        deadline = time.time() + timeout if timeout is not None else None
        while True:
            job.refresh()
            if job.is_finished:
                return job.result
            if job.is_failed:
                raise RuntimeError(job.exc_info or "Job failed")
            if deadline is not None and time.time() > deadline:
                raise TimeoutError("Job result timed out")
            time.sleep(poll_interval)

    def enqueue_at(self, queue_name: str, task_name: str, scheduled_time: datetime, *args, job_id: str | None = None, **kwargs):
        """Enqueue a task to run at a specific time"""
        if self.error:
            return False

        try:
            queue = self.get_queue(queue_name)
            if not queue:
                logger.error(f"Queue {queue_name} not found")
                return False

            task_func = TASK_MAP.get(task_name)
            if not task_func:
                logger.error(f"Unknown task: {task_name}")
                return False

            logger.info(
                f"enqueue_at: queue={queue_name}, func={task_func}, scheduled_time={scheduled_time}, job_id={job_id}, args={args}, kwargs={kwargs}"
            )
            job = queue.enqueue_at(scheduled_time, task_func, *args, job_id=job_id, **kwargs)
            logger.info(f"enqueue_at: created job {job.id} scheduled for {scheduled_time}")
            return job
        except Exception as e:
            logger.exception(f"Failed to schedule task {task_name}: {e}")
            return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled or queued job (including cron jobs)

        This method handles both:
        1. Cancelling any currently queued/running job instance
        2. Removing the cron job definition so it won't reschedule

        Args:
            job_id: The job ID to cancel

        Returns:
            True if at least one (job or cron entry) was cancelled, False if neither existed
        """
        if self.error or not self._redis:
            return False

        cancelled = False

        # Try to fetch and cancel any existing job instance
        try:
            job = Job.fetch(job_id, connection=self._redis)
            job.cancel()
            job.delete()
            logger.info(f"Cancelled and deleted job instance {job_id}")
            cancelled = True
        except Exception as e:
            logger.debug(f"No job instance found for {job_id}: {e}")

        try:
            cron_registered = False
            if hasattr(self._redis, "hexists"):
                cron_registered = bool(self._redis.hexists(CRON_DEFS_KEY, job_id))
            elif hasattr(self._redis, "hget"):
                cron_registered = self._redis.hget(CRON_DEFS_KEY, job_id) is not None

            if not cron_registered and hasattr(self._redis, "zscore"):
                cron_registered = self._redis.zscore(CRON_NEXT_KEY, job_id) is not None

            if cron_registered and self.unregister_cron_job(job_id):
                logger.info(f"Removed cron job registration {job_id}")
                cancelled = True
            else:
                logger.debug(f"No cron registration found for {job_id}")
        except Exception as e:
            logger.debug(f"Failed to remove cron registration for {job_id}: {e}")

        if not cancelled:
            logger.warning(f"Job {job_id} not found (neither job instance nor cron registration)")

        return cancelled

    def get_queue_status(self) -> tuple[dict, int]:
        """Get queue status"""
        if self.error:
            return {"error": "Could not reach Redis", "url": ""}, 500
        return {"status": "🚀 Up and running 🏃", "url": self.redis_url}, 200

    def get_task(self, task_id) -> tuple[dict, int]:
        """Get task status"""
        if self.error:
            return {"error": "Could not reach Redis"}, 500

        try:
            job = Job.fetch(task_id, connection=self._redis)
            response: dict[str, Any] = {"id": task_id}
            if job.is_finished:
                response.update({"status": "SUCCESS", "result": job.result})
                return response, 200
            if job.is_failed:
                response.update({"status": "FAILURE", "error": str(job.exc_info)})
                return response, 500
            response["status"] = "STARTED"
            return response, 202
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return {"error": "Task not found"}, 404

    def collect_osint_source(self, source_id: str, task_id: str):
        """Trigger OSINT source collection"""
        if self.enqueue_task("collectors", "collector_task", source_id, True, job_id=task_id):
            logger.info(f"Collect for source {source_id} scheduled")
            return {"message": f"Refresh for source {source_id} scheduled"}, 200
        logger.error(f"Could not schedule collection for source {source_id}")
        return {"error": "Could not reach Redis"}, 500

    def preview_osint_source(self, source_id: str):
        """Preview OSINT source collection"""
        if job := self.enqueue_task("collectors", "collector_preview", source_id, job_id=f"source_preview_{source_id}"):
            logger.info(f"Preview for source {source_id} scheduled")
            return {"message": f"Preview for source {source_id} scheduled", "id": job.id, "status": "STARTED"}, 201
        return {"error": "Could not reach Redis"}, 500

    @classmethod
    def _get_single_fetch_url(cls, parameters: dict[str, Any]) -> str:
        return get_simple_web_collector_url(parameters)

    @staticmethod
    def _normalize_single_fetch_job_id_value(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                str(key): QueueManager._normalize_single_fetch_job_id_value(value[key]) for key in sorted(value, key=lambda item: str(item))
            }
        if isinstance(value, (list, tuple)):
            return [QueueManager._normalize_single_fetch_job_id_value(item) for item in value]
        if isinstance(value, set):
            normalized_items = [QueueManager._normalize_single_fetch_job_id_value(item) for item in value]
            return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @classmethod
    def _get_single_fetch_job_payload(cls, parameters: dict[str, Any]) -> dict[str, Any]:
        return {
            "url": get_simple_web_collector_url(parameters),
            "parameters": cls._normalize_single_fetch_job_id_value(parameters.get("parameters", {})),
        }

    @classmethod
    def _get_single_fetch_job_id(cls, parameters: dict[str, Any]) -> str:
        payload_json = json.dumps(cls._get_single_fetch_job_payload(parameters), sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        return f"fetch_single_news_item_{payload_hash}"

    def fetch_single_news_item(self, parameters: dict[str, Any]):
        url = get_simple_web_collector_url(parameters)
        job = self.enqueue_task(
            "collectors",
            "fetch_single_news_item",
            parameters,
            job_id=self._get_single_fetch_job_id(parameters),
        )
        if not job:
            logger.error("Could not schedule fetch_single_news_item task")
            return {"error": "Could not reach Redis"}, 500

        logger.info(f"Fetch for single news item {url} scheduled")
        try:
            return self._await_job_result(job)
        except TimeoutError:
            logger.error("Timed out waiting for fetch_single_news_item result for %s", url)
        except Exception:
            logger.exception("Failed to fetch single news item")
        return {"error": "Failed to fetch single news item"}, 500

    def collect_all_osint_sources(self):
        """Trigger collection for all enabled sources"""
        from core.model.osint_source import OSINTSource

        if self.error:
            return {"error": "Could not reach Redis"}, 500

        sources = OSINTSource.get_all_for_collector()
        for source in sources:
            self.enqueue_task("collectors", "collector_task", source.id, True, job_id=source.task_id)
            logger.info(f"Collect for source {source.id} scheduled")
        return {"message": f"Refresh for {len(sources)} sources scheduled"}, 200

    def push_to_connector(self, connector_id: str, story_ids: list):
        """Push stories to connector"""
        if self.enqueue_task("connectors", "connector_task", connector_id, story_ids):
            logger.info(f"Connector with id: {connector_id} scheduled")
            return {"message": f"Connector with id: {connector_id} scheduled"}, 200
        return {"error": "Could not reach Redis"}, 500

    def pull_from_connector(self, connector_id: str):
        """Pull from connector"""
        if self.enqueue_task("connectors", "connector_task", connector_id, None):
            logger.info(f"Connector with id: {connector_id} scheduled")
            return {"message": f"Connector with id: {connector_id} scheduled"}, 200
        return {"error": "Could not reach Redis"}, 500

    def gather_word_list(self, word_list_id: int):
        """Gather word list"""
        if self.enqueue_task("misc", "gather_word_list", word_list_id, job_id=f"gather_word_list_{word_list_id}"):
            logger.info(f"Gathering for WordList {word_list_id} scheduled")
            return {"message": f"Gathering for WordList {word_list_id} scheduled"}, 200
        return {"error": "Could not reach Redis"}, 500

    def execute_bot_task(self, bot_id: str, filter: dict | None = None):
        bot_args: dict[str, str | dict] = {"bot_id": bot_id}
        if filter:
            bot_args["filter"] = filter

        if self.enqueue_task("bots", "bot_task", job_id=f"bot_{bot_id}", **bot_args):
            logger.info(f"Executing Bot {bot_id} scheduled")
            return {"message": f"Executing Bot {bot_id} scheduled", "id": bot_id}, 200
        return {"error": "Could not reach Redis"}, 500

    def generate_product(self, product_id: str, countdown: int = 0):
        """Generate product"""
        from datetime import timedelta

        if countdown > 0:
            scheduled_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=countdown)
            job = self.enqueue_at("presenters", "presenter_task", scheduled_time, product_id, job_id=f"presenter_task_{product_id}")
        else:
            job = self.enqueue_task("presenters", "presenter_task", product_id, job_id=f"presenter_task_{product_id}")

        if job:
            logger.info(f"Generating Product {product_id} scheduled")
            return {"message": f"Generating Product {product_id} scheduled"}, 200
        return {"error": "Could not reach Redis"}, 500

    def publish_product(self, product_id: str, publisher_id: str):
        """Publish product"""
        if self.enqueue_task("publishers", "publisher_task", product_id, publisher_id, job_id=f"publisher_task_{product_id}"):
            logger.info(f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled")
            return {"message": f"Publishing Product: {product_id} with publisher: {publisher_id} scheduled"}, 200
        logger.error(f"Could not schedule publishing for product {product_id} with publisher {publisher_id}")
        return {"error": "Could not reach Redis"}, 500

    def post_collection_bots(self, source_id: str):
        """Run post-collection bots"""
        from core.model.bot import Bot

        post_collection_bots = list(Bot.get_post_collection())
        if not post_collection_bots:
            return {"message": "No post collection bots found"}, 200

        previous_job = None
        for bot_id in post_collection_bots:
            bot_args = {"bot_id": bot_id, "filter": {"SOURCE": source_id}}
            job = self.enqueue_task(
                "bots",
                "bot_task",
                job_id=f"bot_{bot_id}_{source_id}",
                depends_on=previous_job,
                **bot_args,
            )
            if not job:
                return {"error": f"Could not schedule post collection bot {bot_id}"}, 500
            previous_job = job

        return {"message": f"Post collection bots scheduled for source {source_id}"}, 200

    def _get_job_display_name(self, job: Job) -> str:
        """Get human-readable name for a job based on its function and args"""
        if func_name := job.func_name:
            return job.meta.get("name", func_name.split(".")[-1].replace("_", " ").title())
        return job.id or "Unknown Task"

    @staticmethod
    def build_cron_schedule_entry(
        *,
        job_id: str,
        name: str,
        queue: str,
        cron_schedule: str,
        now: datetime | None = None,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        """Build a normalized cron schedule entry."""
        if now is None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

        cron = croniter(cron_schedule, now)
        next_run = cron.get_next(datetime)
        prev_run = croniter(cron_schedule, now).get_prev(datetime)

        entry: dict[str, Any] = {
            "id": job_id,
            "name": name,
            "queue": queue,
            "next_run_time": next_run,
            "previous_run_time": prev_run or None,
            "schedule": cron_schedule,
            "type": "cron",
            "last_run": None,
            "last_success": None,
            "last_status": None,
        }
        entry.update(extra_fields)
        return entry

    def _get_cron_schedule_entries(self) -> list[dict[str, Any]]:
        """Fetch cron-based schedule entries from the current RQ-backed configuration."""
        if not self._redis:
            return []

        all_jobs: list[dict[str, Any]] = []
        try:
            from core.model.bot import Bot
            from core.model.osint_source import OSINTSource

            all_jobs.extend(OSINTSource.get_enabled_schedule_entries())
            all_jobs.extend(Bot.get_enabled_schedule_entries())

            cleanup_result = self._get_latest_task_result(
                exact_ids={TOKEN_CLEANUP_JOB_ID},
                prefixes=[f"cron_{TOKEN_CLEANUP_JOB_ID}_"],
                task_name=TOKEN_CLEANUP_JOB_ID,
            )
            all_jobs.append(
                self.build_cron_schedule_entry(
                    job_id=TOKEN_CLEANUP_JOB_ID,
                    name=TOKEN_CLEANUP_DISPLAY_NAME,
                    queue="misc",
                    cron_schedule=TOKEN_CLEANUP_CRON,
                    task_id=TOKEN_CLEANUP_JOB_ID,
                    last_run=cleanup_result.last_run if cleanup_result else None,
                    last_success=cleanup_result.last_success if cleanup_result else None,
                    last_status=cleanup_result.status if cleanup_result else None,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to fetch cron schedules: {e}")
            # Don't fail the whole request if cron scheduler is not available

        return all_jobs

    @staticmethod
    def _get_latest_task_result(*, exact_ids: set[str] | None = None, prefixes: list[str] | None = None, task_name: str | None = None):
        from core.model.task import Task as TaskModel

        return TaskModel.get_latest_matching(exact_ids=exact_ids, prefixes=prefixes, task_name=task_name)

    def get_scheduled_job(self, task_id: str) -> tuple[dict, int]:
        try:
            job = Job.fetch(task_id, connection=self._redis)
            return {
                "id": job.id,
                "name": job.func_name,
                "scheduled_for": job.enqueued_at.isoformat() if job.enqueued_at else None,
                "status": job.get_status(),
            }, 200
        except Exception:
            cron_job = next((entry for entry in self._get_cron_schedule_entries() if entry.get("id") == task_id), None)
            if not cron_job:
                return {"error": "Job not found"}, 404

            annotated_job = _annotate_jobs([cron_job])[0]
            for field in ("last_run", "last_success", "next_run_time", "previous_run_time"):
                value = annotated_job.get(field)
                if isinstance(value, datetime):
                    annotated_job[field] = value.isoformat()
            return annotated_job, 200

    def get_scheduled_jobs(self) -> tuple[dict, int]:
        """Get all scheduled jobs across all queues

        Returns both:
        1. Jobs currently in the scheduled registry (enqueued but waiting to run)
        2. Cron jobs registered with the cron scheduler
        """
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.registry import ScheduledJobRegistry

            all_jobs = []

            # 1. Get jobs from scheduled registries (already enqueued, waiting to run)
            for queue_name, queue in self._queues.items():
                registry = ScheduledJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
                if job_ids:
                    logger.debug(f"Queue {queue_name}: found {len(job_ids)} scheduled jobs in registry")

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self._redis)
                        # Get scheduled time from registry for this specific job
                        scheduled_time = registry.get_scheduled_time(job_id)

                        logger.debug(f"Job {job_id}: func={job.func_name}, scheduled_time={scheduled_time}")

                        scheduled_for: datetime | None = None
                        if isinstance(scheduled_time, datetime):
                            scheduled_for = (
                                scheduled_time.astimezone(timezone.utc).replace(tzinfo=None) if scheduled_time.tzinfo else scheduled_time
                            )

                        # Get human-readable name from job args
                        job_name = self._get_job_display_name(job)

                        all_jobs.append(
                            {"id": job.id, "name": job_name, "queue": queue_name, "next_run_time": scheduled_for, "type": "scheduled"}
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch job {job_id} from queue {queue_name}: {e}")
                        continue

            # 2. Get cron schedules from database (since cron jobs are in scheduler's memory)
            all_jobs.extend(self._get_cron_schedule_entries())

            annotated_jobs = _annotate_jobs(all_jobs)
            for job in annotated_jobs:
                for field in ("last_run", "last_success", "next_run_time", "previous_run_time"):
                    value = job.get(field)
                    if isinstance(value, datetime):
                        job[field] = value.isoformat()

            logger.info(f"get_scheduled_jobs: returning {len(annotated_jobs)} total jobs")
            return {"items": annotated_jobs, "total_count": len(annotated_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get scheduled jobs: {e}")
            return {"error": f"Failed to get scheduled jobs: {str(e)}"}, 500

    def register_cron_job(self, spec: CronSpec) -> bool:
        if self.error or not self._redis:
            logger.error("QueueManager not initialized, cannot register cron job")
            return False

        payload = json.dumps(spec.model_dump(mode="json"))
        next_ts: float | None = None
        try:
            next_ts = _compute_next_timestamp(spec.cron, spec.interval, time.time())
        except Exception as exc:
            logger.warning(f"Unable to precompute next run for cron job {spec.job_id}: {exc}")

        try:
            with self._redis.pipeline() as p:
                p.hset(CRON_DEFS_KEY, spec.job_id, payload)
                if next_ts is not None:
                    p.zadd(CRON_NEXT_KEY, {spec.job_id: next_ts})
                p.xadd(CRON_EVENTS_KEY, {"op": "upsert", "job_id": spec.job_id})
                p.execute()
                return True
        except Exception as e:
            logger.error(f"Failed to register cron job {spec.job_id}: {e}")
            self.error = f"Could not reach Redis: {e}"
            return False

    def unregister_cron_job(self, job_id: str) -> bool:
        if self.error or not self._redis:
            logger.error("QueueManager not initialized, cannot unregister cron job")
            return False

        try:
            with self._redis.pipeline() as p:
                p.hdel(CRON_DEFS_KEY, job_id)
                p.zrem(CRON_NEXT_KEY, job_id)
                p.xadd(CRON_EVENTS_KEY, {"op": "delete", "job_id": job_id})
                p.execute()
                return True
        except Exception as e:
            logger.error(f"Failed to unregister cron job {job_id}: {e}")
            self.error = f"Could not reach Redis: {e}"
            return False

    def get_cron_job_configs(self) -> tuple[dict[str, list[dict[str, Any]]] | dict[str, str], int]:
        try:
            from core.model.bot import Bot
            from core.model.osint_source import OSINTSource

            cron_jobs: list[dict[str, Any]] = []

            for source in OSINTSource.get_all_for_collector():
                if not (cron_schedule := source.get_schedule_with_default()):
                    continue

                cron_jobs.append(
                    {
                        "task": "collector_task",
                        "queue": "collectors",
                        "args": [source.id, False],
                        "cron": cron_schedule,
                        "task_id": source.task_id,
                        "name": source.name,
                    }
                )

            for bot_item in Bot.get_all_for_collector():
                if not (cron_schedule := bot_item.get_schedule()):
                    continue

                cron_jobs.append(
                    {
                        "task": "bot_task",
                        "queue": "bots",
                        "args": [bot_item.id],
                        "cron": cron_schedule,
                        "task_id": bot_item.task_id,
                        "name": bot_item.name,
                    }
                )

            cron_jobs.append(
                {
                    "task": TOKEN_CLEANUP_JOB_ID,
                    "queue": "misc",
                    "args": [],
                    "cron": TOKEN_CLEANUP_CRON,
                    "task_id": TOKEN_CLEANUP_JOB_ID,
                    "name": "Cleanup Token Blacklist",
                }
            )

            return {"cron_jobs": cron_jobs}, 200
        except Exception:
            logger.exception("Failed to get cron job configurations")
            return {"error": "Failed to get cron job configurations"}, 500

    def get_active_jobs(self) -> tuple[dict, int]:
        """Get currently running jobs from StartedJobRegistry"""
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.registry import StartedJobRegistry

            active_jobs = []
            for queue_name, queue in self._queues.items():
                registry = StartedJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self._redis)
                        job_name = self._get_job_display_name(job)

                        active_jobs.append(
                            {
                                "id": job.id,
                                "name": job_name,
                                "queue": queue_name,
                                "started_at": job.started_at.isoformat() if job.started_at else None,
                                "status": "running",
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to fetch active job {job_id}: {e}")
                        continue

            return {"items": active_jobs, "total_count": len(active_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get active jobs: {e}")
            return {"error": f"Failed to get active jobs: {str(e)}"}, 500

    def get_failed_jobs(self) -> tuple[dict, int]:
        """Get failed jobs from FailedJobRegistry"""
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.registry import FailedJobRegistry

            failed_jobs = []
            for queue_name, queue in self._queues.items():
                registry = FailedJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self._redis)
                        job_name = self._get_job_display_name(job)

                        failed_jobs.append(
                            {
                                "id": job.id,
                                "name": job_name,
                                "queue": queue_name,
                                "failed_at": job.ended_at.isoformat() if job.ended_at else None,
                                "error": str(job.exc_info) if job.exc_info else "Unknown error",
                                "status": "failed",
                            }
                        )
                    except NoSuchJobError:
                        try:
                            registry.remove(job_id, delete_job=False)
                        except Exception as cleanup_error:
                            logger.debug(f"Failed to remove stale failed job {job_id}: {cleanup_error}")
                        continue
                    except Exception as e:
                        # Skip jobs that can't be fetched (might have been cleaned up)
                        logger.debug(f"Skipping failed job {job_id}: {e}")
                        continue

            return {"items": failed_jobs, "total_count": len(failed_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get failed jobs: {e}")
            return {"error": f"Failed to get failed jobs: {str(e)}"}, 500

    def get_worker_stats(self) -> tuple[dict, int]:
        """Get worker statistics"""
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.worker import Worker

            workers = Worker.all(connection=self._redis)
            worker_entries = []
            busy_workers = 0
            idle_workers = 0
            for worker in workers:
                if worker.state == "busy":
                    busy_workers += 1
                elif worker.state == "idle":
                    idle_workers += 1

                current_job = worker.get_current_job()
                worker_entries.append(
                    {
                        "name": worker.name,
                        "state": worker.state,
                        "queues": [q.name for q in worker.queues],
                        "current_job": current_job.id if current_job else None,
                    }
                )

            worker_stats = {
                "total_workers": len(workers),
                "busy_workers": busy_workers,
                "idle_workers": idle_workers,
                "workers": worker_entries,
            }

            return worker_stats, 200
        except Exception as e:
            logger.exception(f"Failed to get worker stats: {e}")
            return {"error": f"Failed to get worker stats: {str(e)}"}, 500

    @staticmethod
    def _build_unique_job_id(task_name: str, product_id: str) -> str:
        return f"{task_name}_{product_id}_{time.time_ns()}"

    def autopublish_product(self, product_id: str, auto_publisher_id: str) -> tuple[dict[str, Any], int]:
        """Render a product and publish it once rendering finishes."""
        if self.error or not self._redis:
            logger.error("QueueManager not initialized, cannot autopublish product %s", product_id)
            return {"error": "QueueManager not initialized"}, 500

        presenter_job_id = self._build_unique_job_id("presenter_task", product_id)
        presenter_job = self.enqueue_task("presenters", "presenter_task", product_id, job_id=presenter_job_id)

        if not presenter_job:
            logger.error("Could not schedule presenter job %s for product %s", presenter_job_id, product_id)
            return {"error": f"Could not schedule presenter job for product {product_id}"}, 500

        publisher_job_id = self._build_unique_job_id("publisher_task", product_id)
        publisher_job = self.enqueue_task(
            "publishers",
            "publisher_task",
            product_id,
            auto_publisher_id,
            job_id=publisher_job_id,
            depends_on=presenter_job,
        )

        if not publisher_job:
            logger.error("Could not schedule publisher job %s for product %s", publisher_job_id, product_id)
            return {"error": f"Could not schedule publisher job for product {product_id}"}, 500

        message = f"Autopublishing Product: {product_id} with publisher: {auto_publisher_id} scheduled"
        logger.info(
            "Autopublish scheduled: presenter job %s -> publisher job %s for product %s",
            presenter_job_id,
            publisher_job_id,
            product_id,
        )
        return {
            "message": message,
            "presenter_job_id": presenter_job_id,
            "publisher_job_id": publisher_job_id,
        }, 200


def initialize(app: Flask, initial_setup: bool = True):
    """Initialize the queue manager"""
    global queue_manager
    queue_manager = QueueManager(app)

    if queue_manager.error:
        logger.error(f"QueueManager initialization failed: {queue_manager.error}")
        return

    if initial_setup:
        queue_manager.post_init()
        logger.info("QueueManager initialized successfully")
