from worker.config import Config
from worker.log import logger


def setup_tasks():
    flows = []

    if "Presenters" in Config.WORKER_TYPES:
        try:
            from worker.flows.presenter_task_flow import presenter_task_flow

            flows.append(presenter_task_flow.to_deployment(name="presenter_task_flow"))
        except OSError as e:
            logger.critical(f"Failed to load PDFPresenter: {e}. Ensure WeasyPrint and dependencies are installed.")

    if "Bots" in Config.WORKER_TYPES:
        try:
            from worker.flows.bot_task_flow import bot_task_flow

            flows.append(bot_task_flow.to_deployment(name="bot_task_flow"))
        except Exception as e:
            logger.critical(f"Failed to load Bot flow: {e}")

    if "Collectors" in Config.WORKER_TYPES:
        try:
            from worker.flows.collector_task_flow import collector_task_flow

            flows.append(collector_task_flow.to_deployment(name="collector_task_flow"))
        except Exception as e:
            logger.critical(f"Failed to load Collector flow: {e}")

    if "Publishers" in Config.WORKER_TYPES:
        try:
            from worker.flows.publisher_task_flow import publisher_task_flow

            flows.append(publisher_task_flow.to_deployment(name="publisher_task_flow"))
        except Exception as e:
            logger.critical(f"Failed to load Publisher flow: {e}")

    if "Connectors" in Config.WORKER_TYPES:
        try:
            from worker.flows.connector_task_flow import connector_task_flow

            flows.append(connector_task_flow.to_deployment(name="connector_task_flow"))
        except Exception as e:
            logger.critical(f"Failed to load Connector flow: {e}")

    return flows
