from celery import Celery

from worker.config import Config
from worker.core_api import CoreApi

import worker.tasks  # noqa: F401


class CeleryWorker:
    def __init__(self):
        celery_config = Config.CELERY

        self.app = Celery(__name__)
        self.app.config_from_object(celery_config)
        self.app.set_default()
        self.core_api = CoreApi()


if __name__ == "worker":
    cw = CeleryWorker()
    celery = cw.app
