"""Data-only HTTP contracts. Nothing here is wired into application requests."""

import re
from copy import copy
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model


class ErrorResponse(BaseModel):
    error: str


class JWTErrorResponse(BaseModel):
    msg: str


class MessageResponse(BaseModel):
    message: str


class IdMessageResponse(MessageResponse):
    id: str


class ItemsResponse[T](BaseModel):
    items: list[T]


class PageResponse[T](BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[T]
    total_count: int = Field(ge=0)


def partial_model(model: type[BaseModel]) -> type[BaseModel]:
    """Allow omitted fields while retaining constraints on explicitly supplied values."""
    fields = {}
    for name, original in model.model_fields.items():
        optional = copy(original)
        optional.default = None
        optional.default_factory = None
        fields[name] = (original.annotation, optional)
    return create_model(f"{model.__name__}Update", __base__=model, **fields)


class EmptyParameters(BaseModel):
    # Unknown query parameters have historically been ignored.
    model_config = ConfigDict(extra="ignore")


class DownloadHeaders(BaseModel):
    content_type: str = Field(min_length=1)
    content_length: int | None = Field(default=None, ge=0)
    content_disposition: str | None = None


class UploadMetadata(BaseModel):
    filename: str | None
    content_type: str | None
    content_length: int | None = Field(default=None, ge=0)


class FileUpload(BaseModel):
    file: UploadMetadata


@dataclass(frozen=True)
class ResponseContract:
    body: Any
    media_type: str | None = "application/json"
    download: bool = False
    json_body: Any = None


def json_response(model: Any) -> ResponseContract:
    return ResponseContract(model)


def download_response(media_type: str | None = None, *, json_body: Any = None) -> ResponseContract:
    return ResponseContract(DownloadHeaders, media_type=media_type, download=True, json_body=json_body)


ERROR_RESPONSES = {
    status: json_response(ErrorResponse | JWTErrorResponse)
    for status in (400, 401, 403, 404, 405, 409, 413, 415, 416, 422, 429, 500, 501, 502, 503, 504)
}


@dataclass(frozen=True)
class ApiEndpointModels:
    method: str
    path: str
    responses: dict[int, ResponseContract]
    body: Any = None
    query: type[BaseModel] = EmptyParameters
    parameters: type[BaseModel] = EmptyParameters
    headers: type[BaseModel] = EmptyParameters
    repeated_query: tuple[str, ...] = ()
    request_media_types: tuple[str, ...] = ("application/json",)
    uploads: type[BaseModel] | None = None
    file_body: bool = False
    alternate_bodies: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Construct path models once with the inventory, without matching requests.
        names = re.findall(r"\{(\w+)\}", self.path)
        if names and self.parameters is EmptyParameters:
            definitions: dict[str, Any] = {name: (str, Field(min_length=1)) for name in names}
            object.__setattr__(self, "parameters", create_model("PathParameters", **definitions))
