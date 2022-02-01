from schema.publisher import PublisherSchema
from managers import log_manager

class BasePublisher:
    type = "BASE_PUBLISHER"
    name = "Base Publisher"
    description = "Base abstract type for all publishers"

    parameters = []

    def get_info(self):
        info_schema = PublisherSchema()
        return info_schema.dump(self)

    def publish(self, publisher_input):
        pass

    def print_exception(self, error):
        log_manager.log_debug_trace("[{0}] {1}".format(self.name, error))
