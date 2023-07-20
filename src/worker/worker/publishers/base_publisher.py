from worker.log import logger


class BasePublisher:
    type = "BASE_PUBLISHER"
    name = "Base Publisher"
    description = "Base abstract type for all publishers"

    parameters = []

    def publish(self, publisher_input):
        pass

    def print_exception(self, error):
        logger.log_debug_trace(f"Publishing Failed: {self.type} - {error}")
