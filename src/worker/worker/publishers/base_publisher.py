from worker.log import logger
from worker.core_api import CoreApi


class BasePublisher:
    def __init__(self):
        self.type = "BASE_PUBLISHER"
        self.name = "Base Publisher"
        self.description = "Base abstract type for all publishers"
        self.core_api = CoreApi()

    def publish(self, publisher_input):
        pass

    def print_exception(self, error):
        logger.log_debug_trace(f"Publishing Failed: {self.type} - {error}")
