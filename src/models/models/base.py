from pydantic import BaseModel
from typing import ClassVar, TypeVar

T = TypeVar("T", bound="TaranisBaseModel")


class TaranisBaseModel(BaseModel):
    _core_endpoint: ClassVar[str]
    _cache_timeout: ClassVar[int]
    _model_name: ClassVar[str] = ""
    _pretty_name: ClassVar[str] = ""

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", False)
        kwargs.setdefault("exclude_unset", False)
        return super().model_dump(*args, **kwargs)
