from prefect import flow, task
from core.log import logger
from models.presenter import PresenterTaskRequest
from core.model.product import Product
from core.model.presenter import Presenter
from core.model.report_item import ReportItem
from worker.presenters.registry import PRESENTER_REGISTRY
import time


@task
def fetch_product_data(product_id: str):
    logger.info("[presenter_task] Fetching product %s", product_id)

    product = Product.get(product_id)
    if not product:
        raise ValueError("Product %s not found" % product_id)

    return product


@task
def get_product_type(product: Product):
    return product.product_type


@task
def fetch_presenter(product_type_id: str):
    logger.info("[presenter_task] Fetching presenter for product type %s", product_type_id)

    presenter = Presenter.get_for_product_type(product_type_id)
    if not presenter:
        raise ValueError("No presenter found for product type %s" % product_type_id)

    return presenter


@task
def fetch_report_items(product: Product, presenter: Presenter):
    logger.info("[presenter_task] Fetching report items for product %s", product.id)

    if hasattr(presenter, "with_limit") and presenter.with_limit:
        return ReportItem.get_for_product(product, limit=presenter.limit)
    return ReportItem.get_for_product(product)


@task
def generate_rendered_product(presenter: Presenter, product: Product, report_items: list):
    logger.info("[presenter_task] Generating rendered product for %s", product.id)

    presenter_class = PRESENTER_REGISTRY.get(presenter.type)
    if not presenter_class:
        raise ValueError(f"Unsupported presenter type: {presenter.type}")

    presenter_instance = presenter_class(presenter)
    return presenter_instance.generate(product=product, report_items=report_items)


@task
def save_rendered_product(product: Product, presenter: Presenter, rendered_product):
    logger.info("[presenter_task] Saving rendered product for %s", product.id)

    product.add_render(presenter.type, rendered_product)
    return product


@flow(name="presenter-task-flow")
def presenter_task_flow(request: PresenterTaskRequest):
    try:
        product_id = str(request.product_id) if request and hasattr(request, "product_id") else None
        if not product_id:
            raise ValueError("Product ID is required")

        logger.info("[presenter_task_flow] Starting generation of product: %s", product_id)

        countdown_value = getattr(request, "countdown", 0)
        if countdown_value and countdown_value > 0:
            logger.info("[presenter_task_flow] Waiting %d seconds before execution", countdown_value)
            time.sleep(countdown_value)

        product = fetch_product_data(product_id)
        product_type = get_product_type(product)

        if not product_type or not hasattr(product_type, "id"):
            raise ValueError("Invalid product type")

        presenter = fetch_presenter(product_type.id)
        report_items = fetch_report_items(product, presenter)
        rendered_product = generate_rendered_product(presenter, product, report_items)
        final_product = save_rendered_product(product, presenter, rendered_product)

        logger.info("[presenter_task_flow] Successfully generated product: %s", product_id)
        return {"message": f"Generating Product {product_id} scheduled", "result": final_product}

    except Exception as e:
        logger.exception("[presenter_task_flow] Failed to generate product")
        return {"error": "Could not reach rabbitmq", "details": str(e)}
