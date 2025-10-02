from models.admin import ReportItemAttribute
from models.assess import Story
from datetime import datetime
from pydantic import Field

from models.base import TaranisBaseModel


class ReportItemCpe(TaranisBaseModel):
    id: int | None = None
    value: str


class ReportItem(TaranisBaseModel):
    _core_endpoint = "/analyze/report-items"
    _model_name = "report"
    _search_fields = ["title"]
    _pretty_name = "Report"

    id: str | None = None
    title: str | None = ""
    created: datetime | None = None
    last_updated: datetime | None = None
    completed: bool | None = None
    user_id: int | None = None
    report_item_type_id: int | None = None
    stories: list[Story | str] = Field(default_factory=list)
    attributes: list[ReportItemAttribute] | dict = Field(default_factory=list)
    report_item_cpes: list[ReportItemCpe] = Field(default_factory=list)
