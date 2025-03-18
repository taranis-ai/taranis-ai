from prefect import flow

import worker.publishers
from worker.publishers.base_publisher import BasePublisher
from worker.log import logger
from worker.types import Product
from worker.core_api import CoreApi


def get_product(product_id: int, core_api: CoreApi) -> dict[str, str]:
    if product := core_api.get_product(product_id):
        return product

    raise RuntimeError(f"Product with id {product_id} not found")


def get_publisher(publisher_id: str, core_api: CoreApi) -> dict:
    if publisher := core_api.get_publisher(publisher_id):
        return publisher

    raise RuntimeError(f"Publisher with id {publisher_id} not found")


def get_publisher_type(pub_type: str) -> BasePublisher:
    publishers: dict[str, BasePublisher] = {
        "email_publisher": worker.publishers.EMAILPublisher(),
        "twitter_publisher": worker.publishers.TWITTERPublisher(),
        "wordpress_publisher": worker.publishers.WORDPRESSPublisher(),
        "ftp_publisher": worker.publishers.FTPPublisher(),
        "sftp_publisher": worker.publishers.SFTPPublisher(),
        "misp_publisher": worker.publishers.MISPPublisher(),
    }

    if publisher := publishers.get(pub_type):
        return publisher

    raise ValueError("Publisher type not found")


def get_rendered_product(product_id: int, core_api: CoreApi) -> Product:
    if product := core_api.get_product_render(product_id):
        return product
    raise RuntimeError(f"Product with id {product_id} not found")


@flow(name="publish_product")
def publish_product(self, product_id: int, publisher_id: str):
    core_api = CoreApi()
    try:
        product = get_product(product_id, core_api)
        publisher = get_publisher(publisher_id, core_api)
        rendered_product = get_rendered_product(product_id, core_api)

        publisher_type = get_publisher_type(publisher["type"])

        return publisher_type.publish(publisher, product, rendered_product)
    except Exception as e:
        logger.exception("Failed to publish product")
        return {"error": str(e)}
