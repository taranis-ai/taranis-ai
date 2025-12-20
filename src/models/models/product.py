from datetime import datetime
from typing import Self

from pydantic import Field, ValidationInfo, field_validator
from requests import Response

from models.base import TaranisBaseModel


class WorkerProduct(TaranisBaseModel):
    data: bytes | None = None
    mime_type: str | None = None

    @classmethod
    def from_response(cls, response: Response) -> Self:
        return cls(
            data=response.content,
            mime_type=response.headers.get("Content-Type", ""),
        )


class Product(TaranisBaseModel):
    _core_endpoint = "/publish/products"
    _model_name = "product"
    _pretty_name = "Product"

    id: str | None = None
    title: str
    description: str | None = ""
    created: datetime | None = None
    auto_publish: bool | None = None
    default_publisher: str | None = None
    product_type_id: int
    report_items: list[str] = Field(default_factory=list)
    last_rendered: datetime | None = None
    render_result: str | None = None
    mime_type: str | None = None

    @field_validator("default_publisher", mode="after")
    @classmethod
    def require_default_when_autopublish(cls, value: str, info: ValidationInfo):
        auto_publish = info.data.get("auto_publish")
        if auto_publish and not value:
            raise ValueError("default_publisher is required when auto_publish is enabled")
        return value
