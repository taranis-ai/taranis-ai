from celery import Celery

from worker.config import Config
from worker.core_api import CoreApi


class TaranisWorker:
    def __init__(self):
        celery_config = Config.CELERY

        self.app = Celery(__name__)
        self.app.config_from_object(celery_config)
        self.app.set_default()
        self.core_api = CoreApi()
