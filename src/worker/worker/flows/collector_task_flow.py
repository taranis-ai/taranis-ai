from prefect import flow, task
from core.log import logger
from models.publisher import PublisherTaskRequest
from core.model.product import Product
from core.model.publisher import Publisher


@task
def fetch_product_info(product_id: str):
    logger.info(f"[publisher_task] Fetching product {product_id}")

    product = Product.get(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    return product


@task
def fetch_publisher_info(publisher_id: str):
    logger.info(f"[publisher_task] Fetching publisher {publisher_id}")

    publisher = Publisher.get(publisher_id)
    if not publisher:
        raise ValueError(f"Publisher {publisher_id} not found")

    return publisher


@task
def get_rendered_product(product: Product, publisher: Publisher):
    logger.info(f"[publisher_task] Getting rendered product for {product.id} with publisher type {publisher.type}")

    rendered_product = product.get_render(publisher.type)
    return rendered_product


@task
def dispatch_publisher(publisher: Publisher, rendered_product):
    logger.info(f"[publisher_task] Dispatching to publisher type: {publisher.type}")

    publisher_module = __import__(f"worker.publishers.{publisher.type}_publisher", fromlist=["PublisherTask"])
    publisher_task_class = getattr(publisher_module, "PublisherTask")

    publisher_instance = publisher_task_class(publisher)
    result = publisher_instance.publish(data=rendered_product.data, file_name_prefix=rendered_product.mime_type)

    logger.info(f"[publisher_task] Published product successfully")
    return result


@flow(name="publisher-task-flow")
def publisher_task_flow(request: PublisherTaskRequest):
    try:
        logger.info(f"[publisher_task_flow] Starting publication of product {request.product_id} with publisher {request.publisher_id}")

        # Fetch  data
        product = fetch_product_info(request.product_id)
        publisher = fetch_publisher_info(request.publisher_id)

        # Get rendered product
        rendered_product = get_rendered_product(product, publisher)

        # Dispatch to publisher
        result = dispatch_publisher(publisher, rendered_product)

        logger.info(f"[publisher_task_flow] Successfully published product {request.product_id}")
        return {"message": f"Publishing Product: {request.product_id} with publisher: {request.publisher_id} scheduled", "result": result}

    except Exception as e:
        logger.exception(f"[publisher_task_flow] Failed to publish product {request.product_id}")
        return {"error": "Could not reach rabbitmq", "details": str(e)}
