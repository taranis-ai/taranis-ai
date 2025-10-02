from datetime import datetime
from pydantic import Field

from models.base import TaranisBaseModel


class WorkerProduct(TaranisBaseModel):
    data: bytes | None = None
    mime_type: str | None = None


class Product(TaranisBaseModel):
    _core_endpoint = "/publish/products"
    _model_name = "product"
    _search_fields = ["title", "description"]
    _pretty_name = "Product"

    id: str | None = None
    title: str
    description: str | None = ""
    created: datetime | None = None
    auto_publish: bool | None = None
    product_type_id: int
    report_items: list[str] = Field(default_factory=list)
    last_rendered: datetime | None = None
    render_result: str | None = None
    mime_type: str | None = None
