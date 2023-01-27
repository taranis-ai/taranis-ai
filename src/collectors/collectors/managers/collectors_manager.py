import threading
import importlib

from collectors.managers.log_manager import logger
from collectors.remote.core_api import CoreApi
from collectors.config import Config


collectors = {}
status_report_thread = None

def initialize():
    CoreApi().register_node()

    logger.log_info(f"Initializing collector node: {Config.NODE_NAME}...")

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

    collectors[collector_type].refresh()
    return 200


def refresh():
    for collector_type in collectors:
        if refresh_collector(collector_type) != 200:
            return 500

    return 200


def get_registered_collectors_info():
    return [collectors[key].get_info() for key in collectors]
