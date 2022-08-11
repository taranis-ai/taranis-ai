from publishers.publishers.ftp_publisher import FTPPublisher
from publishers.publishers.email_publisher import EMAILPublisher
from publishers.publishers.twitter_publisher import TWITTERPublisher
from publishers.publishers.wordpress_publisher import WORDPRESSPublisher
from publishers.publishers.misp_publisher import MISPPublisher
from shared.schema.publisher import PublisherInputSchema

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
    return [publishers[key].get_info() for key in publishers]


def publish(publisher_input_json):
    publisher_input_schema = PublisherInputSchema()
    publisher_input = publisher_input_schema.load(publisher_input_json)
    publishers[publisher_input.type].publish(publisher_input)
