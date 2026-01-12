import mimetypes
from datetime import datetime
from typing import Any

from worker.core_api import CoreApi
from worker.log import logger
from worker.types import Product


class BasePublisher:
    REQUIRED_PARAMETERS: tuple[str, ...] = ()

    def __init__(self):
        self.type = "BASE_PUBLISHER"
        self.name = "Base Publisher"
        self.description = "Base abstract type for all publishers"
        self.file_name: str = f"Taranis_product_{datetime.now().strftime('%d-%m-%Y_%H-%M')}"
        self.core_api = CoreApi()

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> str:
        raise NotImplementedError

    def print_exception(self, error):
        logger.exception(f"Publishing Failed: {self.type} - {error}")

    def set_file_name(self, product):
        self.file_name = BasePublisher.get_file_name(product)

    @staticmethod
    def get_file_name(product) -> str:
        product_title = product.get("title")
        mime_type = product.get("mime_type")

        file_extension = mimetypes.guess_extension(mime_type, strict=False)
        return f"{product_title.replace(' ', '_').lower()}_{datetime.now().strftime('%d-%m-%Y_%H-%M')}{file_extension}"

    def _extract_parameters(self, publisher: dict[str, Any]) -> dict[str, Any]:
        parameters = publisher.get("parameters") or {}
        missing = [param for param in self.REQUIRED_PARAMETERS if not parameters.get(param)]
        if missing:
            missing_params = ", ".join(missing)
            raise ValueError(f"Missing required parameters for {self.name}: {missing_params}")
        return parameters
