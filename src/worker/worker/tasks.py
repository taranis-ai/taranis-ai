from worker.config import Config
from worker.log import logger


def setup_tasks():
    flows = []
    from worker.misc.misc_tasks import debug_flow

    flows.append(debug_flow.to_deployment(name="debug_task"))

    if "Presenters" in Config.WORKER_TYPES:
        try:
            from worker.presenters.presenter_flow import presenter_flow  # noqa: F401

            flows.append(presenter_flow.to_deployment(name="presenter_flow"))
        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    # TODO: migrate to prefect
    # if "Bots" in Config.WORKER_TYPES:
    #     import worker.bots.bot_tasks  # noqa: F401

    # if "Collectors" in Config.WORKER_TYPES:
    #     import worker.collectors.collector_tasks  # noqa: F401

    # if "Publishers" in Config.WORKER_TYPES:
    #     import worker.publishers.publisher_tasks  # noqa: F401

    # if "Connectors" in Config.WORKER_TYPES:
    #     import worker.connectors.connector_tasks  # noqa: F401

    return flows
