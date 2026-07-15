from typing import Any

from models.product import WorkerProduct as Product

from worker.publishers.base_publisher import BasePublisher


class TaranisPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "TARANIS_PUBLISHER"
        self.name = "Taranis Publisher"
        self.description = "Publisher for making products publicly available in Taranis"

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> dict[str, Any]:
        product_id = product.get("id")
        if not product_id:
            raise ValueError("Product has no id")
        if (result := self.core_api.publish_product_to_taranis(product_id)) is not None:
            return result
        raise RuntimeError("Taranis failed to store the published product")
