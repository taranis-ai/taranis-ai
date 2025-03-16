from worker.config import Config
from worker.log import logger


def setup_tasks():
    import worker.misc.misc_tasks  # noqa: F401

    if "Bots" in Config.WORKER_TYPES:
        from worker.bots.bot_tasks import BotTask  # noqa: F401

    if "Collectors" in Config.WORKER_TYPES:
        from worker.collectors.collector_tasks import CollectorTask  # noqa: F401

    if "Presenters" in Config.WORKER_TYPES:
        try:
            from worker.presenters.presenter_tasks import PresenterTask  # noqa: F401
        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    if "Publishers" in Config.WORKER_TYPES:
        from worker.publishers.publisher_tasks import PublisherTask  # noqa: F401
