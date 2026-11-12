"""Realtime proxy and administrative control payloads."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from models.api import MessageResponse, OperationContract, json_response
from models.base import TaranisBaseModel


class Broadcast(BaseModel):
    message: str = Field(max_length=500)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message is required")
        return value


class Client(BaseModel):
    client_id: str
    user_id: str
    username: str


class Clients(BaseModel):
    num_clients: int
    num_users: int
    clients: list[Client]


class Callback(TaranisBaseModel):
    # Centrifugo can add callback metadata independently of Taranis releases.
    client: str | None = None
    transport: str | None = None
    protocol: str | None = None
    encoding: str | None = None
    name: str | None = None
    version: str | None = None


class ProxyHeaders(BaseModel):
    proxy_key: str = Field(alias="X-Realtime-Proxy-Key", min_length=1)


class Disconnect(BaseModel):
    code: Literal[4501]
    reason: Literal["unauthorized"]


class Disconnected(BaseModel):
    disconnect: Disconnect


class Connection(BaseModel):
    user: str
    expire_at: int
    channels: list[str]


class Connected(BaseModel):
    result: Connection


OPERATIONS = (
    OperationContract(
        "POST",
        "/realtime/broadcast",
        {200: json_response(MessageResponse)},
        body=Broadcast,
    ),
    OperationContract("GET", "/realtime/clients", {200: json_response(Clients)}),
    OperationContract(
        "POST", "/realtime/connect", {200: json_response(Connected | Disconnected)}, body=Callback | None, headers=ProxyHeaders
    ),
)
