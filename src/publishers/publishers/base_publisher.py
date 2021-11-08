from schema.publisher import PublisherSchema


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
        print('Publisher name: ' + self.name)
        if str(error).startswith('b'):
            print('ERROR: ' + str(error)[2:-1])
        else:
            print('ERROR: ' + str(error))
