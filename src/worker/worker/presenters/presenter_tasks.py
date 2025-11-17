"""RQ Presenter Tasks

Functions for generating products/reports in various formats.
"""
from base64 import b64encode
from requests.exceptions import ConnectionError
from typing import Any
from rq import get_current_job

import worker.presenters
from worker.presenters.base_presenter import BasePresenter
from worker.log import logger
from worker.core_api import CoreApi


def presenter_task(product_id: str):
    """Generate a product/report in the specified format.
    
    Args:
        product_id: ID of the product to render
    
    Returns:
        dict: Result containing product_id, message, and base64-encoded rendered content
    
    Raises:
        ValueError: If product not found, misconfigured, or rendering fails
        ConnectionError: If unable to connect to core API
    """
    job = get_current_job()
    core_api = CoreApi()
    
    logger.info(f"Starting presenter task with job id {job.id if job else 'manual'}")
    
    # Get product configuration
    product = _get_product(core_api, product_id)
    
    # Get presenter for product type
    presenter = _get_presenter(product)
    
    # Get template if needed
    type_id: int = int(product["type_id"])
    if "TEMPLATE_PATH" in product.get("parameters", {}):
        template = _get_template(core_api, type_id)
    else:
        template = None
    
    logger.info(f"Rendering product {product_id} with presenter {presenter.type}")
    
    # Generate the product
    if rendered_product := presenter.generate(product, template, parameters=product.get("parameters", {})):
        if isinstance(rendered_product, str):
            rendered_product = b64encode(rendered_product.encode("utf-8")).decode("ascii")
        else:
            rendered_product = b64encode(rendered_product).decode("ascii")
        
        return {
            "product_id": product_id,
            "message": f"Product: {product_id} rendered successfully",
            "render_result": rendered_product
        }
    
    raise ValueError(f"Presenter {presenter.type} returned no content")


def _get_product(core_api: CoreApi, product_id: str) -> dict[str, Any]:
    """Fetch product configuration from core API.
    
    Args:
        core_api: CoreApi instance
        product_id: ID of the product
    
    Returns:
        Product configuration dictionary
    
    Raises:
        ValueError: If product not found
        ConnectionError: If unable to connect to core API
    """
    try:
        product = core_api.get_product(product_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e
    
    if not product:
        raise ValueError(f"Product with id {product_id} not found")
    
    return product


def _get_template(core_api: CoreApi, presenter_id: int) -> str:
    """Fetch template from core API.
    
    Args:
        core_api: CoreApi instance
        presenter_id: ID of the presenter/template
    
    Returns:
        Template content
    
    Raises:
        ValueError: If template not found
        ConnectionError: If unable to connect to core API
    """
    try:
        template = core_api.get_template(presenter_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e
    
    if not template:
        raise ValueError(f"Template with id {presenter_id} not found")
    
    return template


def _get_presenter(product: dict[str, Any]) -> BasePresenter:
    """Get the appropriate presenter for a product type.
    
    Args:
        product: Product configuration dictionary
    
    Returns:
        Presenter instance
    
    Raises:
        ValueError: If presenter type not found or not implemented
    """
    presenters = {
        "html_presenter": worker.presenters.HTMLPresenter(),
        "json_presenter": worker.presenters.JSONPresenter(),
        "pandoc_presenter": worker.presenters.PANDOCPresenter(),
        "pdf_presenter": worker.presenters.PDFPresenter(),
        "text_presenter": worker.presenters.TextPresenter(),
        "stix_presenter": worker.presenters.STIXPresenter(),
    }
    
    presenter_type = product.get("type")
    if not presenter_type:
        raise ValueError(f"Product {product['id']} has no presenter_type")
    
    if presenter := presenters.get(presenter_type):
        return presenter
    
    raise ValueError(f"Presenter {presenter_type} not implemented")
