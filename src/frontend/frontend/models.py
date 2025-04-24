from enum import StrEnum
from pydantic import BaseModel, Field
from typing import ClassVar, TypeVar

from frontend.config import Config

T = TypeVar("T", bound="TaranisBaseModel")


class TLPLevel(StrEnum):
    CLEAR = "clear"
    GREEN = "green"
    AMBER_STRICT = "amber+strict"
    AMBER = "amber"
    RED = "red"


class TaranisBaseModel(BaseModel):
    _core_endpoint: ClassVar[str]
    _cache_timeout: ClassVar[int] = Config.CACHE_DEFAULT_TIMEOUT
    _model_name: ClassVar[str] = ""

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    id: str
    name: str
    trigger: str
    next_run_time: str


class Address(TaranisBaseModel):
    city: str = ""
    country: str = ""
    street: str = ""
    zip: str = ""


class Organization(TaranisBaseModel):
    _core_endpoint = "/config/organizations"
    _model_name = "organization"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str = ""
    description: str = ""
    address: Address = Field(default_factory=Address)


class Permissions(TaranisBaseModel):
    _core_endpoint = "/config/permissions"
    _model_name = "permission"
    id: str
    name: str
    description: str


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    _model_name = "role"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str = ""
    description: str | None = ""
    permissions: list[str] = Field(default_factory=list[str])
    tlp_level: TLPLevel | None = None


class User(TaranisBaseModel):
    _core_endpoint = "/config/users"
    _model_name = "user"
    _search_fields = ["name", "username"]

    id: int | None = None
    name: str = ""
    organization: Organization | int | dict = Field(default_factory=dict)
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[Role] | list[int] | list[dict] = Field(default_factory=list[Role])
    username: str = ""
    password: str | None = None


class Dashboard(TaranisBaseModel):
    _core_endpoint = "/dashboard"
    _model_name = "dashboard"
    _cache_timeout = 30
    total_news_items: int | None = None
    total_products: int | None = None
    report_items_completed: int | None = None
    report_items_in_progress: int | None = None
    total_database_items: int | None = None
    latest_collected: str | None = None
    schedule_length: int | None = None


class TaranisConfig(TaranisBaseModel):
    default_collector_proxy: str | None = None
    default_collector_interval: str | None = None
    default_tlp_level: TLPLevel | None = None


class Settings(TaranisBaseModel):
    _core_endpoint = "/admin/settings"
    _model_name = "settings"
    _cache_timeout = 30
    id: int = Field(default=1, frozen=True, exclude=True)
    settings: TaranisConfig | None = None


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None


class CacheObject(list):
    def __init__(
        self, iterable=None, page: int = 1, limit: int = 20, order: str = "", links: dict | None = None, total_count: int | None = None
    ):
        iterable = iterable or []
        super().__init__(iterable)
        self.page = page
        self.limit = limit
        self.order = order
        self._total_count = total_count or len(iterable)
        self._links: dict = links or {}

    def __getitem__(self, item):
        result = super().__getitem__(item)
        if isinstance(item, slice):
            return CacheObject(result, page=self.page, limit=self.limit, order=self.order, total_count=self._total_count)
        return result

    @property
    def current_page(self):
        return self.page

    @property
    def offset(self):
        return (self.page - 1) * self.limit

    @property
    def total_pages(self):
        return (self._total_count + self.limit - 1) // self.limit

    @property
    def last_page(self) -> bool:
        return self.page == self.total_pages

    @property
    def first_page(self) -> bool:
        return self.page == 1

    @property
    def current_range(self):
        return f"{self.offset + 1}-{min(self.offset + self.limit, self._total_count)}"

    def search(self, search: str) -> "CacheObject":
        result_object: CacheObject = CacheObject([])
        for co in self:
            for field in co._search_fields:
                value = getattr(co, field, "")
                if search.lower() in str(value).lower():
                    result_object.append(co)
                    break
        return result_object

    def search_and_paginate(self, paging: PagingData | None) -> "CacheObject":
        if not paging:
            return self
        if paging.search:
            return self.search(paging.search).paginate(paging)
        return self.paginate(paging)

    def paginate(self, paging: PagingData | None) -> "CacheObject":
        if not paging:
            return self[self.offset : self.offset + self.limit]
        if paging.order:
            sort_key, direction = paging.order.split("_")
            self.sort(key=lambda x: getattr(x, sort_key), reverse=direction == "desc")
        if paging.page:
            self.page = paging.page
        if paging.limit:
            self.limit = paging.limit

        return self[self.offset : self.offset + self.limit]
