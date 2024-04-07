from celery import Task

import worker.publishers
from worker.publishers.base_publisher import BasePublisher
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError


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
            "twitter_publisher": worker.publishers.TWITTERPublisher(),
            "wordpress_publisher": worker.publishers.WORDPRESSPublisher(),
            "ftp_publisher": worker.publishers.FTPPublisher(),
            "misp_publisher": worker.publishers.MISPPublisher(),
        }

    def get_product(self, product_id: int) -> tuple[dict[str, str] | None, str | None]:
        try:
            product = self.core_api.get_product(product_id)
        except ConnectionError as e:
            logger.critical(e)
            return None, str(e)

        if not product:
            logger.error(f"Product with id {product_id} not found")
            return None, f"Product with id {product_id} not found"
        return product, None

    def get_publisher(self, publisher_id: str) -> tuple[dict[str, str] | None, str | None]:
        try:
            publisher = self.core_api.get_publisher(publisher_id)
        except ConnectionError as e:
            logger.critical(e)
            return None, str(e)

        if not publisher:
            logger.error(f"Publisher with id {publisher_id} not found")
            return None, f"Publisher with id {publisher_id} not found"
        return publisher, None

    def run(self, product_id: int, publisher_id: str):
        err = None

        product, err = self.get_product(product_id)
        if err or not product:
            return err

        publisher, err = self.get_publisher(publisher_id)
        if err or not publisher:
            return err

        logger.debug(f"Publishing to publisher {publisher}")

        pub_type = publisher.get("type")
        if pub_type not in self.publishers:
            return "Publisher type not found"
        publisher_type: BasePublisher = self.publishers[pub_type]

        published_product = publisher_type.publish(publisher, product)
        if error := published_product.get("error"):
            return error

        return published_product.get("message", "Product published successfully")
