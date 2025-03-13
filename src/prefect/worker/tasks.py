from worker.config import Config
from worker.log import logger


def setup_tasks():
    import worker.misc.misc_tasks  # noqa: F401

    if "Bots" in Config.WORKER_TYPES:
        from worker.bots.bot_tasks import BotTask

    if "Collectors" in Config.WORKER_TYPES:
        from worker.collectors.collector_tasks import CollectorTask

    if "Presenters" in Config.WORKER_TYPES:
        try:
            from worker.presenters.presenter_tasks import PresenterTask

        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    if "Publishers" in Config.WORKER_TYPES:

        app.register_task(PublisherTask())

