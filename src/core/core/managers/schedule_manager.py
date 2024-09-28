from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.job import Job

from core.managers import queue_manager
from core.log import logger
from core.managers.db_manager import db

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


class Scheduler:
    _instance = None

    def __new__(cls) -> BackgroundScheduler:
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(engine=db.engine)})
            cls._scheduler.start()
        return cls._scheduler

    @classmethod
    def add_celery_task(cls, task: dict):
        celery_options = task.get("celery", {})
        if existing_task := Scheduler().get_job(task["id"]):
            existing_task.remove()
        Scheduler().add_job(
            func=queue_manager.queue_manager.celery.send_task,
            id=task["id"],
            name=task["name"],
            kwargs=celery_options,
            **task["jobs_params"],
        )

    @classmethod
    def get_periodic_tasks(cls) -> dict:
        jobs = Scheduler().get_jobs()
        items = [cls.serialize_job(job) for job in jobs]
        return {"items": items, "total_count": len(items)}

    @classmethod
    def get_periodic_task(cls, job_id: str) -> dict | None:
        if job := Scheduler().get_job(job_id):
            return cls.serialize_job(job)
        return None

    @classmethod
    def remove_periodic_task(cls, job_id: str):
        if job := Scheduler().get_job(job_id):
            job.remove()
            return True
        logger.warning(f"Job {job_id} not found")
        return False

    @classmethod
    def serialize_job(cls, job: Job) -> dict:
        try:
            return job.__getstate__()
        except Exception:
            return {}


def initialize():
    if not Scheduler().get_job(cleanup_blacklist_periodic_task["id"]):
        Scheduler.add_celery_task(cleanup_blacklist_periodic_task)
    logger.debug(f"Scheduler initialized {Scheduler.get_periodic_tasks()}")
