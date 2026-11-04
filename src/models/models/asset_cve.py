"""Asset-owned CVEs and severity summaries, independent of article matching."""

from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator

from models.asset import AssetGroup
from models.base import TaranisBaseModel


CveSeverity = Literal["critical", "high", "medium", "low", "none", "unknown"]
CVE_SEVERITIES = get_args(CveSeverity)


class AssetCveFilters(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: str = Field(default="", max_length=200)
    group: str = ""
    tag: str = Field(default="", max_length=200)
    severity: Literal["", "critical", "high", "medium", "low", "none", "unknown"] = ""

    @field_validator("search", "tag")
    @classmethod
    def trim_filter(cls, value: str) -> str:
        return value.strip()


class AssetCve(TaranisBaseModel):
    cve_id: str
    severity: CveSeverity = "unknown"
    score: float | None = None
    imported: bool = False
    manual: bool = False
    sources: list[str] = Field(default_factory=list)


class AssetCveSummary(TaranisBaseModel):
    id: str
    name: str
    group_name: str
    tags: list[str]
    counts: dict[CveSeverity, int] = Field(default_factory=lambda: dict.fromkeys(CVE_SEVERITIES, 0))
    total: int = 0


class AssetCveOverview(BaseModel):
    items: list[AssetCveSummary]
    total_count: int
    page: int
    limit: int
    groups: list[AssetGroup]
    tags: list[str]


class AssetCveList(BaseModel):
    asset_id: str
    asset_name: str
    items: list[AssetCve]
    total_count: int
    page: int
    limit: int
