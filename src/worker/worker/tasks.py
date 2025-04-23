from celery import Celery

from worker.config import Config
import worker.misc.misc_tasks  # noqa: F401
from worker.log import logger


def setup_tasks(app: Celery):
    if "Bots" in Config.WORKER_TYPES:
        from worker.bots.bot_tasks import BotTask

        app.register_task(BotTask())
    if "Collectors" in Config.WORKER_TYPES:
        from worker.collectors.collector_tasks import CollectorTask

        app.register_task(CollectorTask())
    if "Presenters" in Config.WORKER_TYPES:
        try:
            from worker.presenters.presenter_tasks import PresenterTask

            app.register_task(PresenterTask())
        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    if "Publishers" in Config.WORKER_TYPES:
        from worker.publishers.publisher_tasks import PublisherTask

        app.register_task(PublisherTask())

    if "Connectors" in Config.WORKER_TYPES:
        from worker.connectors.connector_tasks import ConnectorTask

        app.register_task(ConnectorTask())
