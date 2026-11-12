"""HTTP operation contracts shared by servers and service clients."""

import re
from copy import copy
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, create_model

from models.base import TaranisBaseModel


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str


class JWTErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    msg: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    """Keep field constraints/validators, allowing omission without allowing new nulls."""
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
    body: TypeAdapter | None
    media_type: str | None = "application/json"
    download: bool = False
    json_body: TypeAdapter | None = None

    def validate(self, payload: Any, *, content_type: str) -> Any:
        if self.media_type is not None and content_type.split(";", 1)[0].strip() != self.media_type:
            raise ValueError("Unexpected response content type")
        if self.body is None:
            if payload not in (None, b"", ""):
                raise ValueError("Unexpected response body")
            return None
        return self.body.validate_python(payload)


def json_response(model: Any) -> ResponseContract:
    return ResponseContract(TypeAdapter(model))


def download_response(media_type: str | None = None, *, json_body: Any = None) -> ResponseContract:
    return ResponseContract(
        TypeAdapter(DownloadHeaders),
        media_type=media_type,
        download=True,
        json_body=TypeAdapter(json_body) if json_body is not None else None,
    )


ERROR_RESPONSES = {
    status: json_response(ErrorResponse | JWTErrorResponse)
    for status in (400, 401, 403, 404, 405, 409, 413, 415, 416, 422, 429, 500, 501, 502, 503, 504)
}


@dataclass(frozen=True)
class OperationContract:
    method: str
    path: str
    responses: dict[int, ResponseContract]
    body: TypeAdapter | None = None
    query: type[BaseModel] = EmptyParameters
    parameters: type[BaseModel] = EmptyParameters
    headers: type[BaseModel] = EmptyParameters
    repeated_query: tuple[str, ...] = ()
    request_media_types: tuple[str, ...] = ("application/json",)
    uploads: type[BaseModel] | None = None
    file_body: bool = False
    api_path: bool = True
    alternate_bodies: dict[str, TypeAdapter] = field(default_factory=dict)
    invalid_request_message: str = "Invalid request"
    validation_error_message: str | None = None
    validation_error_model: type[TaranisBaseModel] | None = None
    field_error_messages: dict[str, str] = field(default_factory=dict)
    _pattern: re.Pattern = field(init=False, repr=False)

    def __post_init__(self):
        names = re.findall(r"\{(\w+)\}", self.path)
        if names and self.parameters is EmptyParameters:
            definitions: dict[str, Any] = {name: (str, Field(min_length=1)) for name in names}
            parameters = create_model("PathParameters", **definitions)
            object.__setattr__(self, "parameters", parameters)
        pattern = re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>[^/]+)", re.escape(self.path.rstrip("/")))
        object.__setattr__(self, "_pattern", re.compile(f"^{pattern}/?$"))

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if method.upper() != self.method:
            return None
        match = self._pattern.fullmatch(urlsplit(path).path)
        return match.groupdict() if match else None

    def validate_body(self, payload: Any) -> Any:
        if self.body is None:
            # Existing transports submit an empty JSON object for bodyless actions.
            if payload not in (None, {}):
                raise ValueError("This operation has no request body")
            return None
        return self.body.validate_python(payload)

    def validation_error_response(self, exc: ValidationError) -> dict[str, str]:
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            if (
                message := self.field_error_messages.get(f"{location}:{error['type']}")
                or self.field_error_messages.get(location)
                or self.field_error_messages.get(".".join("*" if isinstance(part, int) else str(part) for part in error["loc"]))
            ):
                return {"error": message}
        if self.validation_error_message is not None:
            return {"error": self.validation_error_message}
        if self.validation_error_model is not None:
            return {"error": self.validation_error_model.format_validation_errors(exc)}
        return TaranisBaseModel.validation_error_response(exc, prefix=self.invalid_request_message)

    def response(self, status: int) -> ResponseContract:
        if response := self.responses.get(status):
            return response
        if status >= 400 and (response := ERROR_RESPONSES.get(status)):
            return response
        raise ValueError("Unexpected response status")
