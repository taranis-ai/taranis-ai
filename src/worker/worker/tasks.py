"""RQ Task Registration

Import all task modules so their functions are available to RQ workers.
Task functions are decorated with @job and will be discovered by RQ.
"""
from worker.config import Config
import worker.misc.misc_tasks  # noqa: F401 -- ensures cleanup task is registered
from worker.log import logger


def register_tasks():
    """Import task modules to register RQ job functions."""
    if "Bots" in Config.WORKER_TYPES:
        import worker.bots.bot_tasks  # noqa: F401

    if "Collectors" in Config.WORKER_TYPES:
        import worker.collectors.collector_tasks  # noqa: F401

    if "Presenters" in Config.WORKER_TYPES:
        try:
            import worker.presenters.presenter_tasks  # noqa: F401
        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    if "Publishers" in Config.WORKER_TYPES:
        import worker.publishers.publisher_tasks  # noqa: F401

    if "Connectors" in Config.WORKER_TYPES:
        import worker.connectors.connector_tasks  # noqa: F401
