from models.base import TaranisBaseModel
from models.types import TLPLevel


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    id: str
    name: str
    trigger: str
    next_run_time: str


class Address(TaranisBaseModel):
    city: str | None = None
    country: str | None = None
    street: str | None = None
    zip: str | None = None


class Organization(TaranisBaseModel):
    _core_endpoint = "/config/organizations"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str
    description: str | None = None
    address: Address | None = None


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str
    description: str | None = None
    permissions: list[str] | None = None
    tlp_level: TLPLevel | None = None


class User(TaranisBaseModel):
    _core_endpoint = "/config/users"
    _search_fields = ["name", "username"]

    id: int | None = None
    name: str
    organization: Organization | int | dict
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[Role] | list[int] | list[dict]
    username: str
    password: str | None = None


class Permissions(TaranisBaseModel):
    _core_endpoint = "/config/permissions"
    id: str
    name: str
    description: str


class Dashboard(TaranisBaseModel):
    _core_endpoint = "/dashboard"
    _cache_timeout = 30
    total_news_items: int | None = None
    total_products: int | None = None
    report_items_completed: int | None = None
    report_items_in_progress: int | None = None
    total_database_items: int | None = None
    latest_collected: str | None = None
    schedule_length: int | None = None
