import threading
import importlib

from collectors.managers.log_manager import logger
from collectors.remote.core_api import CoreApi
from collectors.config import Config


collectors = {}
status_report_thread = None


def register_collector_node():
    try:
        logger.log_debug(f"Registering Collector Node at {Config.TARANIS_NG_CORE_URL}")
        response, code = CoreApi().register_node()
        if code == 200:
            logger.log_info(f"Successfully registered: {response}")
        return response, code
    except Exception:
        logger.log_critical("Registration failed")


def initialize():
    logger.log_info(f"Initializing collector node: {Config.NODE_NAME}...")

    # inform core that this collector node is alive
    # status_report_thread = threading.Thread(target=reportStatus)
    # status_report_thread.daemon = True
    # status_report_thread.start()

    for c in Config.COLLECTOR_LOADABLE_COLLECTORS:
        module_ = importlib.import_module(f"collectors.collectors.{c.lower()}_collector")
        class_ = getattr(module_, f"{c}Collector")
        register_collector(class_())

    logger.log_info("Collector Node initialized")


def register_collector(collector):
    collectors[collector.type] = collector


def refresh_collector(collector_type):
    if collector_type not in collectors:
        return 403

    class RefreshThread(threading.Thread):
        @classmethod
        def run(cls):
            collectors[collector_type].refresh()

    refresh_thread = RefreshThread()
    refresh_thread.start()
    return 200


def refresh():
    for collector_type in collectors:
        if refresh_collector(collector_type) != 200:
            return 500

    return 200


def get_registered_collectors_info():
    return [collectors[key].get_info() for key in collectors]
