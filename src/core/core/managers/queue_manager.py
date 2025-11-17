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
        """Reschedule all enabled OSINT sources and bots"""
        if self.error:
            return
        try:
            from core.model.osint_source import OSINTSource
            from core.model.bot import Bot

            # Schedule all enabled OSINT sources
            sources = OSINTSource.get_all_for_collector()
            for source in sources:
                if source.enabled:
                    source.schedule_osint_source()
            logger.info(f"Rescheduled {len(sources)} OSINT sources")

            # Schedule all enabled bots
            bots = Bot.get_all_for_collector()
            scheduled_bots = 0
            for bot in bots:
                if bot.enabled and bot.get_schedule():
                    bot.schedule_bot()
                    scheduled_bots += 1
            logger.info(f"Rescheduled {scheduled_bots} bots")
        except Exception as e:
            logger.error(f"Failed to reschedule sources and bots: {e}")

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

    def schedule_cron_task(self, queue_name: str, task_name: str, cron_string: str, *args, job_id: str | None = None, **kwargs):
        """Schedule a task using cron expression"""
        if self.error:
            return False

        try:
            from datetime import timezone

            # Calculate next run time from cron expression
            # Use UTC timezone-aware datetime for RQ scheduling
            now_utc = datetime.now(timezone.utc)
            cron = croniter(cron_string, now_utc)
            next_run = cron.get_next(datetime)

            logger.info(f"schedule_cron_task: task={task_name}, cron={cron_string}, next_run={next_run}, job_id={job_id}, args={args}")
            return self.enqueue_at(queue_name, task_name, next_run, *args, job_id=job_id, **kwargs)
        except Exception as e:
            logger.error(f"Failed to schedule cron task {task_name}: {e}")
            return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled or queued job"""
        if self.error:
            return False

        try:
            job = Job.fetch(job_id, connection=self._redis)
            job.cancel()
            job.delete()
            return True
        except Exception as e:
            logger.debug(f"Failed to cancel job {job_id}: {e}")
            return False

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
        if "collector_task" in func_name and job.args:
            try:
                source_id = job.args[0] if len(job.args) > 0 else None
                if source_id:
                    from core.model.osint_source import OSINTSource
                    from core.managers.db_manager import db
                    source = db.session.get(OSINTSource, source_id)
                    if source:
                        return f"Collector: {source.name}"
            except Exception as e:
                logger.debug(f"Failed to get source name for job {job.id}: {e}")

        # For bot tasks, show the bot name
        if "bot_task" in func_name and job.args:
            try:
                bot_id = job.args[0] if len(job.args) > 0 else None
                if bot_id:
                    from core.model.bot import Bot
                    from core.managers.db_manager import db
                    bot = db.session.get(Bot, bot_id)
                    if bot:
                        return f"Bot: {bot.name}"
            except Exception as e:
                logger.debug(f"Failed to get bot name for job {job.id}: {e}")

        # For other tasks, return the function name
        return func_name

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
        """Get all scheduled jobs across all queues"""
        if self.error:
            return {"error": "QueueManager not initialized"}, 500

        try:
            from rq.registry import ScheduledJobRegistry

            all_jobs = []
            for queue_name, queue in self._queues.items():
                registry = ScheduledJobRegistry(queue=queue)
                job_ids = list(registry.get_job_ids())
                logger.debug(f"Queue {queue_name}: found {len(job_ids)} scheduled jobs")

                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self._redis)
                        # Get scheduled time from registry for this specific job
                        scheduled_time = registry.get_scheduled_time(job_id)

                        logger.debug(f"Job {job_id}: func={job.func_name}, scheduled_time={scheduled_time}")

                        # scheduled_time is a datetime object from RQ, not a timestamp
                        if scheduled_time:
                            from datetime import datetime
                            scheduled_for = scheduled_time.isoformat() if isinstance(scheduled_time, datetime) else None
                        else:
                            scheduled_for = None

                        # Get human-readable name from job args
                        job_name = self._get_job_display_name(job)

                        all_jobs.append({
                            "id": job.id,
                            "name": job_name,
                            "queue": queue_name,
                            "next_run_time": scheduled_for,
                        })
                    except Exception as e:
                        logger.error(f"Failed to fetch job {job_id} from queue {queue_name}: {e}")
                        continue

            logger.info(f"get_scheduled_jobs: returning {len(all_jobs)} total jobs")
            return {"items": all_jobs, "total_count": len(all_jobs)}, 200
        except Exception as e:
            logger.exception(f"Failed to get scheduled jobs: {e}")
            return {"error": f"Failed to get scheduled jobs: {str(e)}"}, 500


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
