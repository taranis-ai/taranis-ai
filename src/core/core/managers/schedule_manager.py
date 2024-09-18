from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from core.config import Config
from core.log import logger

cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "jobs_params": {"trigger": "interval", "hours": 8, "max_instances": 1},
    "celery": {"task": "cleanup_token_blacklist", "args": [], "queue": "misc", "task_id": "cleanup_token_blacklist"},
}


class Scheduler:
    _instance = None

    def __new__(cls) -> BackgroundScheduler:
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=Config.SQLALCHEMY_DATABASE_URI)})
        return cls._scheduler

    @classmethod
    def add_celery_task(cls, task: dict):
        celery_options = task.get("celery", {})
        func = "scheduler.jobs:send_celery_task"
        Scheduler().add_job(
            func=func,
            id=task["id"],
            kwargs=celery_options,
            **task["jobs_params"],
        )

    @classmethod
    def get_periodic_tasks(cls) -> list[dict]:
        # return jobs as a python list of dictionaries to be json serializable
        jobs = Scheduler().get_jobs()
        return [job.__getstate__() for job in jobs]


def initialize():
    Scheduler.add_celery_task(cleanup_blacklist_periodic_task)
    logger.debug(f"Scheduler initialized {Scheduler.get_periodic_tasks()}")
