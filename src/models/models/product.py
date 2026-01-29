from datetime import datetime

from pydantic import Field, ValidationInfo, field_validator

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
    default_publisher: str | None = None
    product_type_id: int
    report_items: list[str] = Field(default_factory=list)
    last_rendered: datetime | None = None
    render_result: str | None = None
    mime_type: str | None = None

    @field_validator("auto_publish", mode="before")
    @classmethod
    def normalize_auto_publish(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"yes", "true", "1", "on"}:
                return True
            if lowered in {"no", "false", "0", "off", ""}:
                return False
        return value

    @field_validator("default_publisher", mode="before")
    @classmethod
    def empty_default_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("default_publisher", mode="after")
    @classmethod
    def require_default_when_autopublish(cls, value, info: ValidationInfo):
        auto_publish = info.data.get("auto_publish")
        if auto_publish and not value:
            raise ValueError("default_publisher is required when auto_publish is enabled")
        return value
