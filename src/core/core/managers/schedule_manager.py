from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from prefect import task, flow
from prefect.schedules import Cron
from datetime import datetime, timedelta

from core.log import logger
from core.managers.db_manager import db
from core.config import Config


cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "name": "Cleanup token blacklist",
    "jobs_params": {
        "trigger": CronTrigger.from_crontab("0 2 * * *"),
        "max_instances": 1,
    },
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
        debug_flow.deploy(
            name="debug_flow",
            work_pool_name="docker-pool",
            image="",
            push=False,
            build=False,
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
        logger.debug([job.id for job in jobs])
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
                "next_run_time": job.next_run_time if hasattr(job, "next_run_time") else None,
            }
        except Exception:
            logger.exception("Failed to serialize job")
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


@task(task_run_name="debug_task", log_prints=True)
async def debug_task(name: str) -> None:
    logger.debug(f"Debug task executed: {name}")


@flow(log_prints=True, flow_run_name="debug_flow")
async def debug_flow(names: list[str]) -> None:
    for name in names:
        await debug_task(name=name)


def initialize():
    #    global schedule
    #    schedule = Scheduler()

    #    schedule.add_celery_task(cleanup_blacklist_periodic_task)
    #    logger.debug("Scheduler initialized")

    debug_flow.deploy(
        name="debug_flow",
        work_pool_name="docker-pool",
        image="",
        schedule=Cron("0 0 * * *"),
        push=False,
        build=False,
    )
