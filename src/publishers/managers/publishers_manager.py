from publishers.ftp_publisher import FTPPublisher
from publishers.email_publisher import EMAILPublisher
from publishers.twitter_publisher import TWITTERPublisher
from publishers.wordpress_publisher import WORDPRESSPublisher
from publishers.misp_publisher import MISPPublisher
from schema.publisher import PublisherInputSchema

publishers = {}


def initialize():
    register_publisher(FTPPublisher())
    register_publisher(EMAILPublisher())
    register_publisher(TWITTERPublisher())
    register_publisher(WORDPRESSPublisher())
    register_publisher(MISPPublisher())


def register_publisher(publisher):
    publishers[publisher.type] = publisher


def get_registered_publishers_info():
    publishers_info = []
    for key in publishers:
        publishers_info.append(publishers[key].get_info())

    return publishers_info


def publish(publisher_input_json):
    publisher_input_schema = PublisherInputSchema()
    publisher_input = publisher_input_schema.load(publisher_input_json)
    publishers[publisher_input.type].publish(publisher_input)
