from pydantic import Field
from typing import Any

from models.base import TaranisBaseModel


class User(TaranisBaseModel):
    _core_endpoint = "/users"
    _model_name = "user"
    _search_fields = ["name", "username"]

    id: int | None = None
    username: str = ""
    name: str
    organization: str
    profile: dict[str, Any] | None = None
    permissions: list[str] | None = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
