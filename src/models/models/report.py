from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from models.assess import Story
from models.base import TaranisBaseModel


class ReportItemCpe(TaranisBaseModel):
    id: int | None = None
    value: str


class ReportItemAttribute(TaranisBaseModel):
    id: int | None = None
    attribute: dict[str, str] | None = None
    attribute_id: int | None = None
    attribute_group_id: int | None = None
    title: str | None = None
    description: str | None = None
    index: int | None = None
    required: bool | None = None
    value: str | None = None
    type: str | None = None
    render_data: dict[str, Any] = Field(default_factory=dict)


class ReportItemAttributeGroup(TaranisBaseModel):
    title: str
    attributes: list[ReportItemAttribute] = Field(default_factory=list)


class ReportTypes(TaranisBaseModel):
    _core_endpoint: ClassVar[str] = "/analyze/report-types"
    _model_name: ClassVar[str] = "report_type"
    _pretty_name: ClassVar[str] = "Report Type"

    id: int | None = None
    title: str | None = ""


class ReportItem(TaranisBaseModel):
    _core_endpoint: ClassVar[str] = "/analyze/report-items"
    _model_name: ClassVar[str] = "report"
    _pretty_name: ClassVar[str] = "Report"

    id: str | None = None
    title: str | None = ""
    created: datetime | None = None
    last_updated: datetime | None = None
    completed: bool | None = None
    user_id: int | None = None
    report_item_type_id: int | None = None
    report_item_type: str | None = None
    stories: list[Story | str] | None = None
    used_story_ids: list[str] = Field(default_factory=list)
    grouped_attributes: list[ReportItemAttributeGroup] | None = None
    attributes: list[ReportItemAttribute] | dict[str, str] = Field(default_factory=list)
    report_item_cpes: list[ReportItemCpe] | None = None
