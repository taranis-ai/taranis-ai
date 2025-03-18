from pydantic import BaseModel
from typing import ClassVar


class TaranisBaseModel(BaseModel):
    _core_endpoint: ClassVar[str]

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class Address(TaranisBaseModel):
    city: str
    country: str
    street: str
    zip: str


class Organization(TaranisBaseModel):
    _core_endpoint = "/config/organizations"
    id: int
    name: str
    description: str | None = None
    address: Address | None = None


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    id: int
    name: str
    description: str
    permissions: list[str]
    tlp_level: int | None = None


class User(TaranisBaseModel):
    _core_endpoint = "/config/users"
    _errors = {}

    id: int | None = None
    name: str
    organization: Organization | int | dict
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[Role] | list[int] | list[dict]
    username: str
    password: str | None = None
