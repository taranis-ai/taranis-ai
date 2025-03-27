from pydantic import BaseModel
from typing import ClassVar, TypeVar


T = TypeVar("T", bound="TaranisBaseModel")


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


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    id: str
    name: str
    trigger: str
    next_run_time: str


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


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None


class CacheObject(list):
    def __init__(self, iterable=None, page: int = 1, limit: int = 5, order: str = "", length: int | None = None):
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
            return self[self.offset : self.offset + self.limit]
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
