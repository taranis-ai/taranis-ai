"""Queue Manager for RQ (Redis Queue) task management

This module manages job queues and task scheduling using RQ and Redis.

Architecture:
------------
1. Core Application (this module):
   - Manages RQ queues (collectors, bots, presenters, publishers, etc.)
   - Enqueues immediate tasks via enqueue_task()
   - Provides API endpoints for workers to fetch schedules

2. RQ Cron Scheduler (separate process):
   - Runs as standalone process (src/worker/start_cron_scheduler.py)
   - Loads cron configuration from worker.cron_config module
   - Fetches all enabled sources/bots from Core API
   - Registers cron jobs with RQ using register()
   - Automatically enqueues jobs at specified cron intervals

3. RQ Workers:
   - Pick up enqueued jobs from queues
   - Execute task functions (collectors, bots, etc.)
   - No self-rescheduling logic needed

Schedule Updates:
----------------
When a source/bot schedule is updated:
1. Changes are saved to the database
2. The cron scheduler process will pick up changes on its next reload cycle
3. For immediate updates, restart the cron scheduler process

See: src/worker/worker/cron_config.py for cron job registration logic
"""

from flask import Flask
from redis import Redis
from rq import Queue
from rq.job import Job
from datetime import datetime
from croniter import croniter

from core.log import logger


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
}


class QueueManager:
    def __init__(self, app: Flask):
        self._redis: Redis | None = None
        self._queues: dict[str, Queue] = {}
        self.error: str = ""
        self.redis_url = app.config["REDIS_URL"]
        self.queue_names = ["misc", "bots", "collectors", "presenters", "publishers", "connectors"]

        try:
            self.init_app(app)
        except Exception as e:
            logger.error(f"Failed to initialize QueueManager: {e}")
            self.error = f"Could not connect to Redis: {e}"

    def init_app(self, app: Flask):
        """Initialize Redis connection and create queues"""
        self._redis = Redis.from_url(self.redis_url, decode_responses=False)

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
        """Check enabled sources and bots - cron scheduler will pick them up automatically"""
        if self.error:
            return
        try:
            from core.model.osint_source import OSINTSource
            from core.model.bot import Bot

            # Count enabled sources and bots for logging
            sources = OSINTSource.get_all_for_collector()
            enabled_sources = sum(1 for s in sources if s.enabled and s.get_schedule())
            
            bots = Bot.get_all_for_collector()
            enabled_bots = sum(1 for b in bots if b.enabled and b.get_schedule())
            
            logger.info(
                f"Found {enabled_sources} enabled sources and {enabled_bots} enabled bots with schedules. "
                f"Cron scheduler will automatically pick them up."
            )
        except Exception as e:
            logger.error(f"Failed to check sources and bots: {e}")

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
            tasks = []
            for queue_name, queue in self._queues.items():
                job_count = len(queue)
                tasks.append({"name": queue_name, "messages": job_count})
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

            job = queue.enqueue(
                task_func,
                *args,
                job_id=job_id,
                **kwargs
            )
            return job
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_name}: {e}")
            return False

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

            logger.info(f"enqueue_at: queue={queue_name}, func={task_func}, scheduled_time={scheduled_time}, job_id={job_id}, args={args}, kwargs={kwargs}")
            job = queue.enqueue_at(
                scheduled_time,
                task_func,
                *args,
                job_id=job_id,
                **kwargs
            )
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
            
        # Also remove from cron scheduler (if it's a recurring cron job)
        # This prevents the job from being rescheduled automatically
        try:
            # RQ stores cron jobs with prefix "rq:cron:"
            cron_key = f"rq:cron:{job_id}"
            if self._redis.delete(cron_key):
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
            if job.is_finished:
                return {"result": job.result}, 200
            if job.is_failed:
                return {"error": str(job.exc_info)}, 500
            return {"status": job.get_status()}, 202
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
        """Execute bot task"""
        bot_args: dict = {"bot_id": bot_id}
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
            scheduled_time = datetime.now() + timedelta(seconds=countdown)
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

        # Enqueue each bot sequentially - bots execute in the order they are enqueued
        for bot_id in post_collection_bots:
            bot_args = {"bot_id": bot_id, "filter": {"SOURCE": source_id}}
            self.enqueue_task("bots", "bot_task", job_id=f"bot_{bot_id}_{source_id}", **bot_args)

        return {"message": f"Post collection bots scheduled for source {source_id}"}, 200

    def _get_job_display_name(self, job: Job) -> str:
        """Get human-readable name for a job based on its function and args"""
        func_name = job.func_name or "unknown"

        # For collector tasks, show the source name
        if "collector" in func_name.lower() and job.args:
            try:
                source_id = job.args[0] if len(job.args) > 0 else None
                if source_id:
                    from core.model.osint_source import OSINTSource
                    from core.managers.db_manager import db
                    source = db.session.get(OSINTSource, source_id)
                    if source:
                        return f"Collector: {source.name}"
                    else:
                        logger.debug(f"OSINT Source with ID {source_id} not found in database")
            except Exception as e:
                logger.debug(f"Failed to get source name for job {job.id}: {e}")
            
            # Fallback if source lookup failed
            return f"Collector Task (ID: {job.args[0] if job.args else 'unknown'})"

        # For bot tasks, show the bot name
        if "bot" in func_name.lower() and job.args:
            try:
                bot_id = job.args[0] if len(job.args) > 0 else None
                if bot_id:
                    from core.model.bot import Bot
                    from core.managers.db_manager import db
                    bot = db.session.get(Bot, bot_id)
                    if bot:
                        return f"Bot: {bot.name}"
                    else:
                        logger.debug(f"Bot with ID {bot_id} not found in database")
            except Exception as e:
                logger.debug(f"Failed to get bot name for job {job.id}: {e}")
            
            # Fallback if bot lookup failed
            return f"Bot Task (ID: {job.args[0] if job.args else 'unknown'})"

        # For presenter tasks
        if "presenter" in func_name.lower():
            return f"Presenter: {func_name.split('.')[-1].replace('_', ' ').title()}"

        # For publisher tasks
        if "publisher" in func_name.lower():
            return f"Publisher: {func_name.split('.')[-1].replace('_', ' ').title()}"

        # For maintenance tasks
        if "cleanup" in func_name.lower() or "update" in func_name.lower():
            return f"Maintenance: {func_name.split('.')[-1].replace('_', ' ').title()}"

        # For other tasks, return the function name (last part only)
        return func_name.split('.')[-1].replace('_', ' ').title()

    @staticmethod
    def get_next_fire_times_from_cron(cron_expr: str, n: int = 3) -> list[datetime]:
        """Calculate next n fire times from a cron expression"""
        cron = croniter(cron_expr, datetime.now())
        fire_times: list[datetime] = []

        for _ in range(n):
            try:
                next_time = cron.get_next(datetime)
                fire_times.append(next_time)
            except Exception:
                break

        return fire_times

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
            from datetime import datetime

            all_jobs = []
            
            # 1. Get jobs from scheduled registries (already enqueued, waiting to run)
            for queue_name, queue in self._queues.items():
                registry = ScheduledJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
                logger.debug(f"Queue {queue_name}: found {len(job_ids)} scheduled jobs in registry")

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self._redis)
                        # Get scheduled time from registry for this specific job
                        scheduled_time = registry.get_scheduled_time(job_id)

                        logger.debug(f"Job {job_id}: func={job.func_name}, scheduled_time={scheduled_time}")

                        scheduled_for = scheduled_time.isoformat() if isinstance(scheduled_time, datetime) else None

                        # Get human-readable name from job args
                        job_name = self._get_job_display_name(job)

                        all_jobs.append({
                            "id": job.id,
                            "name": job_name,
                            "queue": queue_name,
                            "next_run_time": scheduled_for,
                            "type": "scheduled"
                        })
                    except Exception as e:
                        logger.error(f"Failed to fetch job {job_id} from queue {queue_name}: {e}")
                        continue

            # 2. Get cron schedules from database (since cron jobs are in scheduler's memory)
            try:
                # Check if any cron schedulers are active
                scheduler_names = self._redis.zrange('rq:cron_schedulers', 0, -1)  # type: ignore
                scheduler_count = len(scheduler_names) if scheduler_names else 0  # type: ignore
                
                if scheduler_count > 0:
                    logger.debug(f"Found {scheduler_count} active cron scheduler(s) - fetching schedules from database")
                    
                    # Import here to avoid circular dependencies
                    from core.model.osint_source import OSINTSource
                    from core.model.bot import Bot
                    from datetime import datetime
                    from croniter import croniter
                    
                    # Get all enabled sources with schedules
                    sources = OSINTSource.get_all_for_collector()
                    for source in sources:
                        if source.enabled and (cron_schedule := source.get_schedule()):
                            try:
                                # Calculate next run time
                                now = datetime.now()
                                cron = croniter(cron_schedule, now)
                                next_run = cron.get_next(datetime)
                                
                                all_jobs.append({
                                    "id": f"cron_collector_{source.id}",
                                    "name": f"Collector: {source.name}",
                                    "queue": "collectors",
                                    "next_run_time": next_run.isoformat(),
                                    "schedule": cron_schedule,
                                    "type": "cron",
                                    "source_id": source.id
                                })
                            except Exception as e:
                                logger.error(f"Failed to calculate next run for source {source.id}: {e}")
                    
                    # Get all enabled bots with schedules
                    bots = Bot.get_all_for_collector()
                    for bot in bots:
                        if bot.enabled and (cron_schedule := bot.get_schedule()):
                            try:
                                # Calculate next run time
                                now = datetime.now()
                                cron = croniter(cron_schedule, now)
                                next_run = cron.get_next(datetime)
                                
                                all_jobs.append({
                                    "id": f"cron_bot_{bot.id}",
                                    "name": f"Bot: {bot.name}",
                                    "queue": "bots",
                                    "next_run_time": next_run.isoformat(),
                                    "schedule": cron_schedule,
                                    "type": "cron",
                                    "bot_id": bot.id
                                })
                            except Exception as e:
                                logger.error(f"Failed to calculate next run for bot {bot.id}: {e}")

                    # Register housekeeping tasks that are scheduled via cron
                    try:
                        now = datetime.now()
                        housekeeping_cron = "0 2 * * *"
                        next_run = croniter(housekeeping_cron, now).get_next(datetime)
                        all_jobs.append({
                            "id": "cron_misc_cleanup_token_blacklist",
                            "name": "Maintenance: Cleanup Token Blacklist",
                            "queue": "misc",
                            "next_run_time": next_run.isoformat(),
                            "schedule": housekeeping_cron,
                            "type": "cron",
                        })
                    except Exception as e:
                        logger.error(f"Failed to calculate next run for housekeeping task cleanup_token_blacklist: {e}")
                else:
                    logger.info("No active cron schedulers found")
                        
            except Exception as e:
                logger.warning(f"Failed to fetch cron schedules: {e}")
                # Don't fail the whole request if cron scheduler is not available

            logger.info(f"get_scheduled_jobs: returning {len(all_jobs)} total jobs")
            return {"items": all_jobs, "total_count": len(all_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get scheduled jobs: {e}")
            return {"error": f"Failed to get scheduled jobs: {str(e)}"}, 500

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

                        active_jobs.append({
                            "id": job.id,
                            "name": job_name,
                            "queue": queue_name,
                            "started_at": job.started_at.isoformat() if job.started_at else None,
                            "status": "running"
                        })
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

                        failed_jobs.append({
                            "id": job.id,
                            "name": job_name,
                            "queue": queue_name,
                            "failed_at": job.ended_at.isoformat() if job.ended_at else None,
                            "error": str(job.exc_info) if job.exc_info else "Unknown error",
                            "status": "failed"
                        })
                    except Exception as e:
                        # Skip jobs that can't be fetched (might have been cleaned up)
                        logger.debug(f"Skipping failed job {job_id}: {e}")
                        continue

            return {"items": failed_jobs, "total_count": len(failed_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get failed jobs: {e}")
            return {"error": f"Failed to get failed jobs: {str(e)}"}, 500

    def retry_failed_job(self, job_id: str) -> tuple[dict, int]:
        """Retry a failed job"""
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            job = Job.fetch(job_id, connection=self._redis)
            
            if job.is_failed:
                # Requeue the job
                job.retry()
                logger.info(f"Retrying failed job {job_id}")
                return {"message": f"Job {job_id} queued for retry"}, 200
            else:
                return {"error": f"Job {job_id} is not in failed state"}, 400

        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            # Job might have been cleaned up already
            if "No such job" in str(e):
                return {"error": f"Job {job_id} not found (may have been already cleaned up)"}, 404
            return {"error": f"Failed to retry job: {str(e)}"}, 500

    def get_worker_stats(self) -> tuple[dict, int]:
        """Get worker statistics"""
        if self.error or not self._redis:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.worker import Worker

            workers = Worker.all(connection=self._redis)
            worker_stats = {
                "total_workers": len(workers),
                "busy_workers": sum(1 for w in workers if w.state == "busy"),
                "idle_workers": sum(1 for w in workers if w.state == "idle"),
                "workers": [
                    {
                        "name": w.name,
                        "state": w.state,
                        "queues": [q.name for q in w.queues],
                        "current_job": w.get_current_job().id if w.get_current_job() else None
                    }
                    for w in workers
                ]
            }

            return worker_stats, 200
        except Exception as e:
            logger.exception(f"Failed to get worker stats: {e}")
            return {"error": f"Failed to get worker stats: {str(e)}"}, 500


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
