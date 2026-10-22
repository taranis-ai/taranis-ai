"""Notify Core after RQ changes the state displayed by task views."""

from collections.abc import Callable
from functools import wraps

from rq import Queue, SpawnWorker, Worker, get_current_job
from rq.defaults import DEFAULT_LOGGING_DATE_FORMAT, DEFAULT_LOGGING_FORMAT
from rq.job import Job
from rq.scheduler import RQScheduler
from rq.utils import current_timestamp
from rq.worker import BaseWorker

from worker.core_api import CoreApi


def task_started[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # SpawnWorker recreates a plain RQ worker in its child. Task entry points
        # run after STARTED has been stored on both fork and spawn platforms.
        if job := get_current_job():
            CoreApi().notify_task_change(job.meta.get("user_id"))
        return function(*args, **kwargs)

    return wrapper


class TaskEventScheduler(RQScheduler):
    def enqueue_scheduled_jobs(self) -> None:
        self._status = self.Status.WORKING
        if not self._scheduled_job_registries and self._acquired_locks:
            self.prepare_registries()
        for registry in self._scheduled_job_registries:
            due_ids = registry.get_jobs_to_schedule(current_timestamp())
            if not due_ids:
                continue
            queue = Queue(registry.name, connection=self.connection, serializer=self.serializer)
            jobs = Job.fetch_many(due_ids, connection=self.connection, serializer=self.serializer)
            # Publish from the same due-job snapshot that is promoted. A second
            # scan could cross a due time and miss that job's notification.
            with self.connection.pipeline() as pipeline:
                for job in jobs:
                    if job is not None:
                        queue._enqueue_job(job, pipeline=pipeline, at_front=job.should_enqueue_at_front())
                for job_id in due_ids:
                    registry.remove(job_id, pipeline=pipeline)
                pipeline.execute()
            user_ids = list(dict.fromkeys(job.meta.get("user_id") for job in jobs if job and job.meta.get("user_id")))
            api = CoreApi()
            # The internal notice accepts bounded batches, including background-only work.
            for offset in range(0, max(1, len(user_ids)), 100):
                api.notify_task_change(*user_ids[offset : offset + 100])
        self._status = self.Status.STARTED


class TaskEventWorker(BaseWorker):
    def execute_job(self, job: Job, queue: Queue) -> None:
        super().execute_job(job, queue)
        # The parent waits for success, retry, failure, or a killed workhorse.
        # Registries and released dependencies are authoritative by this point.
        CoreApi().notify_task_change(job.meta.get("user_id"))

    def register_birth(self) -> None:
        super().register_birth()
        CoreApi().notify_task_change()

    def register_death(self) -> None:
        super().register_death()
        CoreApi().notify_task_change()

    def _start_scheduler(
        self,
        burst: bool = False,
        logging_level: str | None = "INFO",
        date_format: str = DEFAULT_LOGGING_DATE_FORMAT,
        log_format: str = DEFAULT_LOGGING_FORMAT,
    ) -> None:
        # RQ does not expose a scheduler-class option. Keep its lock/start
        # lifecycle while observing delayed-job promotion in the same process.
        self.scheduler = TaskEventScheduler(
            self.queues,
            connection=self.connection,
            logging_level=logging_level if logging_level is not None else self.log.level,
            date_format=date_format,
            log_format=log_format,
            serializer=self.serializer,
        )
        self.scheduler.acquire_locks()
        if not self.scheduler.acquired_locks:
            return
        if not burst:
            self.scheduler.start()
            return
        try:
            self.scheduler.register_birth()
            self.scheduler.enqueue_scheduled_jobs()
        finally:
            self.scheduler.release_locks()
            self.scheduler.register_death()


class TaskEventForkWorker(TaskEventWorker, Worker):
    pass


class TaskEventSpawnWorker(TaskEventWorker, SpawnWorker):
    pass
