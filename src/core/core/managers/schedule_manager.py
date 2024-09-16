from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from core.config import Config

cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "task": "cleanup_token_blacklist",
    "schedule": "daily",
    "options": {"queue": "misc"},
}


class Scheduler:
    _instance = None

    def __new__(cls) -> BackgroundScheduler:
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._scheduler = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=Config.SQLALCHEMY_DATABASE_URI)})
            cls._scheduler.start()
        return cls._scheduler

    @classmethod
    def add_periodic_task(cls, task: dict):
        pass

    @classmethod
    def get_periodic_tasks(cls):
        pass
