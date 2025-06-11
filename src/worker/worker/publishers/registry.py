from worker.publishers.email_publisher import EMAILPublisher
from worker.publishers.ftp_publisher import FTPPublisher
from worker.publishers.sftp_publisher import SFTPPublisher
from worker.publishers.wordpress_publisher import WORDPRESSPublisher
from worker.publishers.misp_publisher import MISPPublisher

PUBLISHER_REGISTRY = {
    "email_publisher": EMAILPublisher,
    "ftp_publisher": FTPPublisher,
    "sftp_publisher": SFTPPublisher,
    "wordpress_publisher": WORDPRESSPublisher,
    "misp_publisher": MISPPublisher,
}
