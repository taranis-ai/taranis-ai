from datetime import datetime
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, ValidationInfo, field_validator
from requests import Response

from models.base import TaranisBaseModel
from models.types import PRESENTER_TYPES, PUBLISHER_TYPES


def validate_linkable_url(value: str | None) -> str | None:
    if value is None:
        return None
    if value != value.strip() or "\\" in value or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("URL is not safe to open")

    if value.startswith("/"):
        if value.startswith("//"):
            raise ValueError("URL is not safe to open")
        return value

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as error:
        raise ValueError("URL is not safe to open") from error
    if parsed.scheme not in {"http", "https"} or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("URL is not safe to open")
    return value


class WorkerProduct(TaranisBaseModel):
    data: bytes | None = None
    mime_type: str | None = None

    @classmethod
    def from_response(cls, response: Response) -> Self:
        return cls(
            data=response.content,
            mime_type=response.headers.get("Content-Type", ""),
        )


class ProductParameterValue(TaranisBaseModel):
    TEMPLATE_PATH: str | None = None


class ProductType(TaranisBaseModel):
    _core_endpoint = "/publish/product-types"
    _model_name = "product_type"
    _pretty_name = "Product Type"

    id: str | None = None
    title: str
    description: str | None = ""
    type: PRESENTER_TYPES
    parameters: ProductParameterValue = Field(default_factory=ProductParameterValue)
    report_types: list[str] = Field(default_factory=list)


class PublisherPreset(TaranisBaseModel):
    _core_endpoint = "/publish/publisher-presets"
    _model_name = "publisher_preset"
    _pretty_name = "Publisher Preset"

    id: str | None = None
    name: str
    type: PUBLISHER_TYPES
    description: str | None = ""
    parameters: dict[str, str] = Field(default_factory=dict)


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
    product_type_id: str
    report_items: list[str] = Field(default_factory=list)
    last_rendered: datetime | None = None
    last_published_url: str | None = None
    render_result: str | None = None
    mime_type: str | None = None

    @field_validator("last_published_url", mode="after")
    @classmethod
    def require_safe_last_published_url(cls, value: str | None) -> str | None:
        return validate_linkable_url(value)

    @field_validator("default_publisher", mode="after")
    @classmethod
    def require_default_when_autopublish(cls, value: str, info: ValidationInfo):
        auto_publish = info.data.get("auto_publish")
        if auto_publish and not value:
            raise ValueError("default_publisher is required when auto_publish is enabled")
        return value
