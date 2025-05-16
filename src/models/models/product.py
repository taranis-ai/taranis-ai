from datetime import datetime
from pydantic import Field

from models.base import TaranisBaseModel


class WorkerProduct(TaranisBaseModel):
    data: bytes | None = None
    mime_type: str | None = None


class Product(TaranisBaseModel):
    id: str | None = None
    title: str
    description: str | None = None
    created: datetime | None = None
    auto_publish: bool | None = None
    product_type_id: int
    report_items: list[str] = Field(default_factory=list)
    last_rendered: datetime | None = None
