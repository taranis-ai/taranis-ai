from typing import Generic, TypeVar

from models.base import TaranisBaseModel
from pydantic import BaseModel

from frontend.config import Config


T = TypeVar("T", bound="TaranisBaseModel")


class PagingData(BaseModel):
    page: int | None = None
    limit: int | None = None
    order: str | None = None
    search: str | None = None
    fetch_all: bool | None = None
    query_params: dict[str, str | list[str]] | None = None

    def set_fetch_all(self) -> "PagingData":
        params = dict(self.query_params or {})
        params["fetch_all"] = "true"
        return self.model_copy(update={"fetch_all": True, "query_params": params})


class CacheObject(list[T], Generic[T]):
    def __init__(
        self,
        iterable: list[T] | None = None,
        page: int = 1,
        limit: int = 20,
        order: str = "",
        links: dict | None = None,
        query_params: dict | None = None,
        total_count: int | None = None,
    ):
        iterable = iterable or []
        super().__init__(iterable)
        self.page = page
        self.limit = limit
        self.order = order
        self._links: dict = links or {}
        self._query_params: dict = query_params or {}
        self._total_count = total_count or len(iterable)

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

    @property
    def items(self) -> list[T]:
        return list(self)
