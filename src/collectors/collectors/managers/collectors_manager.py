import threading
import time
import importlib

from collectors.managers.log_manager import logger
from collectors.remote.core_api import CoreApi
from collectors.config import Config


collectors = {}
status_report_thread = None


def reportStatus():
    while True:
        try:
            logger.log_debug(f"Sending status update to {Config.TARANIS_NG_CORE_URL}")
            response, code = CoreApi().update_collector_status()
            logger.log_debug(f"Core responded with: HTTP {code}, {response}")
        except Exception:
            logger.log_critical("Core update failed")

        time.sleep(Config.CORE_STATUS_UPDATE_INTERVAL)


def initialize():
    logger.log_system_activity(__name__, "Initializing collector...")

    # inform core that this collector node is alive
    # status_report_thread = threading.Thread(target=reportStatus)
    # status_report_thread.daemon = True
    # status_report_thread.start()

    for c in Config.COLLECTOR_LOADABLE_COLLECTORS:
        module_ = importlib.import_module(f"collectors.collectors.{c.lower()}_collector")
        class_ = getattr(module_, f"{c}Collector")
        register_collector(class_())

    logger.log_system_activity(__name__, "Collector initialized.")


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


def update_collector_id(collector_id):
    config_file = Config.COLLECTOR_CONFIG_FILE
    with open(config_file, "w") as file:
        file.write(collector_id)


def get_registered_collectors_info():
    return [collectors[key].get_info() for key in collectors]
