from typing import TypeVar, Generic
from pydantic import BaseModel
from models.base import TaranisBaseModel
from frontend.config import Config

T = TypeVar("T", bound="TaranisBaseModel")


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None


class CacheObject(list[T], Generic[T]):
    def __init__(
        self,
        iterable: list[T] | None = None,
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
        self._total_count = total_count or len(iterable)
        self._links: dict = links or {}

    def __getitem__(self, item):  # type: ignore[override]
        result = super().__getitem__(item)
        if isinstance(item, slice):
            return CacheObject(result, page=self.page, limit=self.limit, order=self.order, total_count=self._total_count)
        return result

    @property
    def timeout(self) -> float | int:
        if self and hasattr(self[0], "_cache_timeout"):
            return getattr(self[0], "_cache_timeout")
        return Config.CACHE_DEFAULT_TIMEOUT

    @property
    def current_page(self) -> int:
        return self.page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

    @property
    def total_pages(self):
        return (self._total_count + self.limit - 1) // self.limit

    @property
    def total_count(self) -> int:
        return self._total_count

    @property
    def last_page(self) -> bool:
        return self.page == self.total_pages

    @property
    def first_page(self) -> bool:
        return self.page == 1

    @property
    def current_range(self):
        return f"{self.offset + 1}-{min(self.offset + self.limit, self._total_count)}"

    def search(self, query: str) -> "CacheObject[T]":
        if not query:
            return self
        q = query.lower()
        hits = []
        for item in self:
            for fld in getattr(item, "_search_fields", []):
                val = getattr(item, fld, None)
                if val is not None and q in str(val).lower():
                    hits.append(item)
                    break
        return CacheObject(
            hits,
            page=1,
            limit=self.limit,
            order=self.order,
            links=self._links,
            total_count=len(hits),
        )

    def order_by(self, paging_order: str) -> "CacheObject[T]":
        key, direction = paging_order.split("_", 1)
        if direction not in ("asc", "desc"):
            raise ValueError(f"Direction must be 'asc' or 'desc', got {direction!r}")

        reverse = direction == "desc"
        try:
            sorted_items = sorted(self, key=lambda x: getattr(x, key), reverse=reverse)
        except AttributeError as e:
            raise ValueError(f"Cannot sort by '{key}': {e}") from e
        new_order = f"{key}_{direction}"
        return CacheObject(
            sorted_items,
            page=1,
            limit=self.limit,
            order=new_order,
            links=self._links,
            total_count=self._total_count,
        )

    def paginate(self, page: int, limit: int | None = None) -> "CacheObject[T]":
        new_limit = limit if limit is not None else self.limit
        new_page = max(1, page)
        result = self[(new_page - 1) * new_limit : (new_page - 1) * new_limit + new_limit]
        result.page = new_page
        result.limit = new_limit
        return result

    def next_page(self) -> "CacheObject[T]":
        return self.paginate(min(self.page + 1, self.total_pages))

    def prev_page(self) -> "CacheObject[T]":
        return self.paginate(max(self.page - 1, 1))

    def search_and_paginate(self, paging: PagingData | None) -> "CacheObject[T]":
        """
        Apply search, ordering, and pagination all at once
        """
        if not paging:
            return self

        result = self

        if paging.search:
            result = result.search(paging.search)

        if paging.order:
            result = result.order_by(paging.order)

        target_page = paging.page or result.page
        target_limit = paging.limit or result.limit
        result = result.paginate(target_page, target_limit)

        return result
