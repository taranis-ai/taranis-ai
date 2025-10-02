from pydantic import Field
from typing import Any

from models.base import TaranisBaseModel


class UserProfile(TaranisBaseModel):
    _core_endpoint = "/users"
    _model_name = "user_profile"
    _search_fields = ["name", "username"]

    id: int | None = None
    username: str = ""
    name: str
    organization: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    permissions: list[str] | None = Field(default_factory=list)
    roles: list[dict[str, Any]] | None = Field(default_factory=list)
