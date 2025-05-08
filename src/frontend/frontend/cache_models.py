from pydantic import BaseModel
from models.base import TaranisBaseModel

from frontend.config import Config


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None


class CacheObject(list):
    def __init__(
        self,
        iterable: list[TaranisBaseModel] | None = None,
        page: int = 1,
        limit: int = 20,
        order: str = "",
        links: dict | None = None,
        total_count: int | None = None,
    ):
        iterable = iterable or []
        super().__init__(iterable)
        self.page = page
        self.limit = limit
        self.order = order
        self.timeout = iterable[0]._cache_timeout if hasattr(iterable[0], "_cache_timeout") else Config.CACHE_DEFAULT_TIMEOUT
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
