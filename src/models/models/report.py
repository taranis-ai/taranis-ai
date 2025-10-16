from typing import ClassVar, Final
from datetime import datetime
from pydantic import Field

from models.admin import ReportItemAttribute
from models.assess import Story
from models.base import TaranisBaseModel


class ReportItemCpe(TaranisBaseModel):
    id: int | None = None
    value: str


class ReportItemAttributeGroup(TaranisBaseModel):
    title: str
    attributes: list[ReportItemAttribute] = Field(default_factory=list)


class ReportItem(TaranisBaseModel):
    _core_endpoint: ClassVar[str] = "/analyze/report-items"
    _model_name: ClassVar[str] = "report"
    _search_fields: Final[list[str]] = ["title"]
    _pretty_name: ClassVar[str] = "Report"

    id: str | None = None
    title: str | None = ""
    created: datetime | None = None
    last_updated: datetime | None = None
    completed: bool | None = None
    user_id: int | None = None
    report_item_type_id: int | None = None
    report_item_type: str | None = None
    stories: list[Story | str] = Field(default_factory=list)
    grouped_attributes: list[ReportItemAttributeGroup] | None = None
    attributes: list[ReportItemAttribute] | dict[str, str] = Field(default_factory=list)
    report_item_cpes: list[ReportItemCpe] = Field(default_factory=list)
