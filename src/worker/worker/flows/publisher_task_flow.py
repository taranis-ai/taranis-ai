from prefect import flow, task
from worker.log import logger
from models.prefect import PublisherTaskRequest
from worker.core_api import CoreApi
from worker.types import Product
import worker.publishers


@task
def get_product_info(product_id: int):
    """Get product information from CoreApi"""
    logger.info(f"[publisher_task] Getting product info for {product_id}")

    core_api = CoreApi()
    product = core_api.get_product(product_id)

    if not product:
        logger.error(f"Product with id {product_id} not found")
        raise RuntimeError(f"Product with id {product_id} not found")

    return product


@task
def get_publisher_info(publisher_id: str):
    """Get publisher information from CoreApi"""
    logger.info(f"[publisher_task] Getting publisher info for {publisher_id}")

    core_api = CoreApi()
    publisher = core_api.get_publisher(publisher_id)

    if not publisher:
        logger.error(f"Publisher with id {publisher_id} not found")
        raise RuntimeError(f"Publisher with id {publisher_id} not found")

    return publisher


@task
def get_rendered_product_info(product_id: int):
    """Get rendered product from CoreApi"""
    logger.debug(f"EMAIL Publisher: Getting rendered product for product {product_id}")

    core_api = CoreApi()
    rendered_product = core_api.get_product_render(product_id)

    if rendered_product is None:
        raise ValueError("Rendered product is None")

    return rendered_product


@task
def get_publisher_instance(publisher: dict):
    """Get publisher instance from registry"""
    logger.info("[publisher_task] Getting publisher instance")

    publishers = {
        "email_publisher": worker.publishers.EMAILPublisher(),
        "wordpress_publisher": worker.publishers.WORDPRESSPublisher(),
        "ftp_publisher": worker.publishers.FTPPublisher(),
        "sftp_publisher": worker.publishers.SFTPPublisher(),
        "misp_publisher": worker.publishers.MISPPublisher(),
    }

    pub_type = publisher.get("type")
    if pub_type not in publishers:
        raise ValueError("Publisher type not found")

    publisher_instance = publishers[pub_type]
    return publisher_instance


@task
def publish_product(publisher_instance, publisher: dict, product: dict, rendered_product: Product):
    """Execute publisher.publish()"""
    logger.debug(f"Publishing to {publisher}")
    logger.debug(f"Product: {product}")

    result = publisher_instance.publish(publisher, product, rendered_product)
    return result


@flow(name="publisher-task-flow")
def publisher_task_flow(request: PublisherTaskRequest):
    try:
        logger.info("[publisher_task_flow] Starting publisher task ")

        # Convert string IDs to int where needed
        product_id = int(request.product_id)
        publisher_id = request.publisher_id

        # Get product info
        product = get_product_info(product_id)

        # Get publisher info
        publisher = get_publisher_info(publisher_id)

        # Get rendered product
        rendered_product = get_rendered_product_info(product_id)

        # Get publisher instance from registry
        publisher_instance = get_publisher_instance(publisher)

        # Execute publish
        result = publish_product(publisher_instance, publisher, product, rendered_product)

        logger.info("[publisher_task_flow] Publisher task completed successfully")

        return result

    except Exception:
        logger.exception("[publisher_task_flow] Publisher task failed")
        raise
