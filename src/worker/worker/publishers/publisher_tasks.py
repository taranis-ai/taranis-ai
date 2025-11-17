"""RQ Publisher Tasks

Functions for publishing products to external systems.
"""
from rq import get_current_job

import worker.publishers
from worker.publishers.base_publisher import BasePublisher
from worker.log import logger
from worker.core_api import CoreApi
from worker.types import Product


def publisher_task(product_id: int, publisher_id: str):
    """Publish a product to an external system.

    Args:
        product_id: ID of the product to publish
        publisher_id: ID of the publisher configuration

    Returns:
        Result from the publisher

    Raises:
        ValueError: If product, publisher, or rendered product not found
        RuntimeError: If product or publisher lookup fails
    """
    job = get_current_job()
    core_api = CoreApi()

    logger.info(f"Starting publisher task with job id {job.id if job else 'manual'}")

    # Get product, publisher, and rendered content
    product = _get_product(core_api, product_id)
    publisher = _get_publisher(core_api, publisher_id)
    rendered_product = _get_rendered_product(core_api, product_id)

    if rendered_product is None:
        raise ValueError("Rendered product is None")

    logger.debug(f"Publishing to {publisher}")
    logger.debug(f"Product: {product}")

    # Get publisher implementation
    pub_type = publisher.get("type")
    publisher_impl = _get_publisher_impl(pub_type)

    return publisher_impl.publish(publisher, product, rendered_product)


def _get_product(core_api: CoreApi, product_id: int) -> dict[str, str]:
    """Fetch product configuration from core API.

    Args:
        core_api: CoreApi instance
        product_id: ID of the product

    Returns:
        Product configuration dictionary

    Raises:
        RuntimeError: If product not found
    """
    product = core_api.get_product(product_id)

    if not product:
        logger.error(f"Product with id {product_id} not found")
        raise RuntimeError(f"Product with id {product_id} not found")

    return product


def _get_publisher(core_api: CoreApi, publisher_id: str) -> dict:
    """Fetch publisher configuration from core API.

    Args:
        core_api: CoreApi instance
        publisher_id: ID of the publisher

    Returns:
        Publisher configuration dictionary

    Raises:
        RuntimeError: If publisher not found
    """
    publisher = core_api.get_publisher(publisher_id)

    if not publisher:
        logger.error(f"Publisher with id {publisher_id} not found")
        raise RuntimeError(f"Publisher with id {publisher_id} not found")

    return publisher


def _get_rendered_product(core_api: CoreApi, product_id: int) -> Product | None:
    """Fetch rendered product from core API.

    Args:
        core_api: CoreApi instance
        product_id: ID of the product

    Returns:
        Rendered product or None if not found
    """
    logger.debug(f"Getting rendered product for product {product_id}")
    return core_api.get_product_render(product_id)


def _get_publisher_impl(pub_type: str) -> BasePublisher:
    """Get publisher implementation for a given type.

    Args:
        pub_type: Publisher type name

    Returns:
        Publisher implementation instance

    Raises:
        ValueError: If publisher type not implemented
    """
    publishers = {
        "email_publisher": worker.publishers.EMAILPublisher(),
        "wordpress_publisher": worker.publishers.WORDPRESSPublisher(),
        "ftp_publisher": worker.publishers.FTPPublisher(),
        "sftp_publisher": worker.publishers.SFTPPublisher(),
        "misp_publisher": worker.publishers.MISPPublisher(),
    }

    if pub_type not in publishers:
        raise ValueError(f"Publisher type '{pub_type}' not found")

    return publishers[pub_type]
