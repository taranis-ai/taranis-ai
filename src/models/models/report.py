from models.admin import ReportItemAttribute
from datetime import datetime
from pydantic import Field

from models.base import TaranisBaseModel


class ReportItemCpe(TaranisBaseModel):
    id: int | None = None
    value: str


class ReportItem(TaranisBaseModel):
    id: str
    title: str | None = None
    created: datetime | None = None
    last_updated: datetime | None = None
    completed: bool | None = None
    user_id: int | None = None
    report_item_type_id: int | None = None
    stories: list[str] = Field(default_factory=list)
    attributes: list[ReportItemAttribute] = Field(default_factory=list)
    report_item_cpes: list[ReportItemCpe] = Field(default_factory=list)
