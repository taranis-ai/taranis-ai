import mimetypes
from datetime import UTC, datetime
from typing import Any

from models.product import WorkerProduct as Product

from worker.core_api import CoreApi
from worker.log import logger
from worker.publishers.execution_context import (
    effective_network_timeout,
    get_publisher_context,
    publisher_network_phase,
    start_publisher_phase,
)


class BasePublisher:
    def __init__(self):
        self.type = "BASE_PUBLISHER"
        self.name = "Base Publisher"
        self.description = "Base abstract type for all publishers"
        self.file_name: str = f"Taranis_product_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}"
        self.core_api = CoreApi()

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> Any:
        raise NotImplementedError

    def print_exception(self, error):
        logger.error(f"Publishing failed: type={self.type} exception_type={type(error).__name__}")

    def set_file_name(self, product):
        self.file_name = BasePublisher.get_file_name(product)

    @staticmethod
    def get_file_name(product) -> str:
        product_title = product.get("title")
        mime_type = product.get("mime_type")

        file_extension = mimetypes.guess_extension(mime_type, strict=False) or ""
        return f"{product_title}_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}{file_extension}"

    def _extract_parameters(self, publisher: dict[str, Any]) -> dict[str, Any]:
        return publisher.get("parameters") or {}

    def _network_timeout(self, parameters: dict[str, Any]) -> float:
        return effective_network_timeout(parameters)

    def _start_phase(self, phase: str) -> None:
        start_publisher_phase(phase)

    def _start_close_phase(self) -> None:
        context = get_publisher_context()
        if context is None or context.failure_phase is None:
            start_publisher_phase("close")

    def _network_phase(self, phase: str, timeout: float):
        return publisher_network_phase(phase, timeout, self.type)

    @staticmethod
    def _require_rendered_data(rendered_product: Product) -> bytes:
        if rendered_product.data is None:
            raise ValueError("Rendered product data is required")
        return rendered_product.data
