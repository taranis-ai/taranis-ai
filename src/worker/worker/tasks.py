from celery import Celery

from worker.config import Config
from worker.presenters.presenter_tasks import PresenterTask
from worker.collectors.collector_tasks import CollectorTask
from worker.bots.bot_tasks import BotTask
from worker.publishers.publisher_tasks import PublisherTask
import worker.misc.misc_tasks  # noqa: F401


def setup_tasks(app: Celery):
    if "Bots" in Config.WORKER_TYPES:
        app.register_task(BotTask())
    if "Collectors" in Config.WORKER_TYPES:
        app.register_task(CollectorTask())
    if "Presenters" in Config.WORKER_TYPES:
        app.register_task(PresenterTask())
    if "Publishers" in Config.WORKER_TYPES:
        app.register_task(PublisherTask())
