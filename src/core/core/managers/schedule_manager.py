from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.job import Job

from core.managers import queue_manager
from core.log import logger
from core.managers.db_manager import db
from core.config import Config


cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "name": "Cleanup token blacklist",
    "jobs_params": {"trigger": "interval", "hours": 8, "max_instances": 1},
    "celery": {
        "args": [],
        "queue": "misc",
        "task_id": "cleanup_token_blacklist",
        "name": "cleanup_token_blacklist",
    },
}

schedule: "Scheduler"


class Scheduler:
    def __init__(self):
        self._scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(engine=db.engine)})
        self.start()

    def start(self):
        if Config.DISABLE_SCHEDULER:
            logger.info("Scheduler is disabled")
            return
        self._scheduler.start()

    def add_celery_task(self, task: dict):
        celery_options = task.get("celery", {})
        self.add_job(
            func=queue_manager.queue_manager.celery.send_task,
            id=task["id"],
            name=task["name"],
            kwargs=celery_options,
            **task["jobs_params"],
            replace_existing=True,
        )

    @property
    def scheduler(self):
        return self._scheduler

    def add_job(self, **kwargs):
        self._scheduler.add_job(**kwargs)

    def get_jobs(self) -> list[Job]:
        return self._scheduler.get_jobs()

    def get_job(self, job_id: str) -> Job | None:
        return self._scheduler.get_job(job_id)

    def get_periodic_tasks(self) -> dict:
        jobs = self.get_jobs()
        logger.debug([self.serialize_job(job) for job in jobs])
        items = [self.serialize_job(job) for job in jobs]
        return {"items": items, "total_count": len(items)}

    def get_periodic_task(self, job_id: str) -> dict | None:
        if job := self.get_job(job_id):
            return self.serialize_job(job)
        return None

    def remove_periodic_task(self, job_id: str):
        if job := self.get_job(job_id):
            job.remove()
            return True
        logger.warning(f"Job {job_id} not found")
        return False

    def serialize_job(self, job: Job) -> dict:
        try:
            return {
                "id": job.id,
                "trigger": str(job.trigger),
                "args": str(job.args),
                "kwargs": str(job.kwargs),
                "name": job.name,
                "next_run_time": job.next_run_time,
            }
        except Exception:
            logger.exception("Failed to serialize job")
            return {}


def initialize():
    global schedule
    schedule = Scheduler()

    schedule.add_celery_task(cleanup_blacklist_periodic_task)
    logger.debug("Scheduler initialized")
