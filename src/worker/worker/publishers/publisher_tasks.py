from celery import Task

import worker.publishers
from worker.publishers.base_publisher import BasePublisher
from worker.log import logger
from worker.core_api import CoreApi
from worker.types import Product


class PublisherTask(Task):
    name = "publisher_task"
    max_retries = 3
    priority = 6
    default_retry_delay = 60
    time_limit = 60

    def __init__(self):
        self.core_api = CoreApi()
        self.publishers = {
            "email_publisher": worker.publishers.EMAILPublisher(),
            "wordpress_publisher": worker.publishers.WORDPRESSPublisher(),
            "ftp_publisher": worker.publishers.FTPPublisher(),
            "sftp_publisher": worker.publishers.SFTPPublisher(),
            "misp_publisher": worker.publishers.MISPPublisher(),
        }

    def get_product(self, product_id: int) -> dict[str, str]:
        product = self.core_api.get_product(product_id)

        if not product:
            logger.error(f"Product with id {product_id} not found")
            raise RuntimeError(f"Product with id {product_id} not found")
        return product

    def get_publisher(self, publisher_id: str) -> dict:
        publisher = self.core_api.get_publisher(publisher_id)

        if not publisher:
            logger.error(f"Publisher with id {publisher_id} not found")
            raise RuntimeError(f"Publisher with id {publisher_id} not found")
        return publisher

    def get_rendered_product(self, product_id: int) -> Product | None:
        logger.debug(f"EMAIL Publisher: Getting rendered product for product {product_id}")
        return self.core_api.get_product_render(product_id)

    def run(self, product_id: int, publisher_id: str):
        product = self.get_product(product_id)
        publisher = self.get_publisher(publisher_id)
        rendered_product = self.get_rendered_product(product_id)
        if rendered_product is None:
            raise ValueError("Rendered product is None")

        logger.debug(f"Publishing to {publisher}")
        logger.debug(f"Product: {product}")

        pub_type = publisher.get("type")
        if pub_type not in self.publishers:
            raise ValueError("Publisher type not found")
        publisher_type: BasePublisher = self.publishers[pub_type]

        return publisher_type.publish(publisher, product, rendered_product)
