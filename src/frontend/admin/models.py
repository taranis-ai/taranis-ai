from enum import StrEnum
from pydantic import BaseModel
from typing import ClassVar, TypeVar

from admin.config import Config

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

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)


class Address(TaranisBaseModel):
    city: str | None = None
    country: str | None = None
    street: str | None = None
    zip: str | None = None


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    id: str
    name: str
    trigger: str
    next_run_time: str


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


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None


class CacheObject(list):
    def __init__(self, iterable=None, page: int = 1, limit: int = 20, order: str = "", length: int | None = None):
        iterable = iterable or []
        super().__init__(iterable)
        self.page = page
        self.limit = limit
        self.order = order
        self.length = length or len(iterable)

    def __getitem__(self, item):
        result = super().__getitem__(item)
        if isinstance(item, slice):
            return CacheObject(result, page=self.page, limit=self.limit, order=self.order, length=self.length)
        return result

    @property
    def current_page(self):
        return self.page

    @property
    def offset(self):
        return (self.page - 1) * self.limit

    @property
    def total_pages(self):
        return (self.length + self.limit - 1) // self.limit

    @property
    def last_page(self) -> bool:
        return self.page == self.total_pages

    @property
    def first_page(self) -> bool:
        return self.page == 1

    @property
    def current_range(self):
        return f"{self.offset + 1}-{min(self.offset + self.limit, self.length)}"

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
