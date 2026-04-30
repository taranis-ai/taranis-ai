"""RQ Publisher Tasks

Functions for publishing products to external systems.
"""

from models.product import WorkerProduct as Product
from models.task_submission_meta import WorkerTaskPayload
from rq import get_current_job

import worker.publishers
from worker.core_api import CoreApi
from worker.log import logger
from worker.publishers.base_publisher import BasePublisher


def publisher_task(payload: WorkerTaskPayload):
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
    publisher_id = payload["worker_id"]
    product_id = str(payload["product_id"])
    core_api = CoreApi()
    task_name = "publisher_task"
    task_id = job.id if job else f"{task_name}_{publisher_id}_{product_id}"
    worker_type = "publisher_task"

    logger.info(f"Starting publisher task with job id {job.id if job else 'manual'}")

    try:
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
        if pub_type is None:
            raise ValueError(f"Publisher {publisher_id} has no type configured")
        worker_type = pub_type
        publisher_impl = _get_publisher_impl(pub_type)

        result = publisher_impl.publish(publisher, product, rendered_product)
        core_api.save_task_result(task_id, task_name, result, "SUCCESS", worker_id=publisher_id, worker_type=worker_type)
        return result
    except Exception as exc:
        core_api.save_task_result(
            task_id,
            task_name,
            {"error": str(exc)},
            "FAILURE",
            worker_id=publisher_id,
            worker_type=worker_type,
        )
        raise


def _get_product(core_api: CoreApi, product_id: str) -> dict[str, str]:
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


def _get_rendered_product(core_api: CoreApi, product_id: str) -> Product | None:
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
        "s3_publisher": worker.publishers.S3Publisher(),
        "taxii_publisher": worker.publishers.TAXIIPublisher(),
    }

    if pub_type not in publishers:
        raise ValueError(f"Publisher type '{pub_type}' not found")

    return publishers[pub_type]
