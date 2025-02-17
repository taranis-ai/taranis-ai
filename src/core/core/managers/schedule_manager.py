from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from datetime import datetime, timedelta

from core.managers import queue_manager
from core.log import logger
from core.managers.db_manager import db
from core.config import Config

cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "name": "Cleanup token blacklist",
    "jobs_params": {
        "trigger": CronTrigger.from_crontab("0 */8 * * *"),
        "max_instances": 1,
    },
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
            if not Config.DISABLE_SCHEDULER:
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
            return {
                "id": job.id,
                "trigger": str(job.trigger),
                "args": str(job.args),
                "kwargs": str(job.kwargs),
                "name": job.name,
                "next_run_time": job.next_run_time,
            }
        except Exception:
            return {}

    @classmethod
    def get_next_n_fire_times_from_cron(cls, cron_expr: str, n: int = 3) -> list[datetime]:
        trigger = CronTrigger.from_crontab(cron_expr)
        now = datetime.now(trigger.timezone) if trigger.timezone else datetime.now()

        fire_times: list[datetime] = []
        current: datetime = now

        while len(fire_times) != n:
            next_fire: datetime | None = trigger.get_next_fire_time(None, current)
            if next_fire is None:
                break
            fire_times.append(next_fire)
            current = next_fire + timedelta(microseconds=1)

        return fire_times


def initialize():
    if not Scheduler().get_job(cleanup_blacklist_periodic_task["id"]):
        Scheduler.add_celery_task(cleanup_blacklist_periodic_task)
    logger.debug("Scheduler initialized")
