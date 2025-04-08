from pydantic import BaseModel
from typing import ClassVar, TypeVar

T = TypeVar("T", bound="TaranisBaseModel")


class TaranisBaseModel(BaseModel):
    _core_endpoint: ClassVar[str]
    _cache_timeout: ClassVar[int]

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)
