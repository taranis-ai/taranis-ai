from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from models.assess import StoryTag
from models.base import TaranisBaseModel


DashboardHealthState = Literal["up", "down", "n/a"]


class DashboardHealthServices(BaseModel):
    database: DashboardHealthState
    seed_data: DashboardHealthState
    broker: DashboardHealthState
    workers: DashboardHealthState


class DashboardHealth(BaseModel):
    healthy: bool
    services: DashboardHealthServices


class CoreHealth(TaranisBaseModel):
    _core_endpoint = "/health"
    _model_name = "core_health"
    _pretty_name = "Core Health"
    _cache_timeout = 5

    healthy: bool
    services: DashboardHealthServices


class TaskStatusTotals(BaseModel):
    successes: int = 0
    failures: int = 0
    total: int = 0
    success_pct: int = 0


class Dashboard(TaranisBaseModel):
    _core_endpoint = "/dashboard"
    _model_name = "dashboard"
    _pretty_name = "Dashboard"
    _cache_timeout = 30
    total_news_items: int = 0
    total_story_items: int = 0
    total_products: int = 0
    report_items_completed: int = 0
    report_items_in_progress: int = 0
    latest_collected: datetime | None = None
    schedule_length: int | None = None
    conflict_count: int | None = None
    health_status: DashboardHealth | None = None
    task_status_totals: TaskStatusTotals | None = None


class PizzintStatus(TaranisBaseModel):
    _core_endpoint = "/dashboard/pizzint"
    _model_name = "pizzint_status"
    _pretty_name = "PizzINT Status"
    _cache_timeout = 60

    state: Literal["fresh", "stale", "unavailable"] = "unavailable"
    level: int | None = Field(default=None, ge=1, le=5, strict=True)
    smoothed_index: float | None = Field(default=None, ge=0, le=100, strict=True)
    observed_at: datetime | None = None
    fetched_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500, strict=True)

    @model_validator(mode="after")
    def validate_available_status(self) -> Self:
        if self.state == "unavailable":
            return self
        if None in (self.level, self.smoothed_index, self.observed_at, self.fetched_at) or not self.reason or not self.reason.strip():
            raise ValueError("Available PizzINT status requires all fields")
        if self.observed_at is None or self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("PizzINT observation time must include a timezone")
        if self.fetched_at is None or self.fetched_at.tzinfo is None or self.fetched_at.utcoffset() is None:
            raise ValueError("PizzINT fetch time must include a timezone")
        self.observed_at = self.observed_at.astimezone(UTC)
        self.fetched_at = self.fetched_at.astimezone(UTC)
        self.reason = self.reason.strip()
        return self


class TrendingCluster(TaranisBaseModel):
    _core_endpoint = "/dashboard/trending-clusters"
    _model_name = "trending_clusters"
    _pretty_name = "Trending Clusters"

    name: str
    tags: list[StoryTag] = Field(default_factory=list)
    size: int | None = None


class Cluster(TaranisBaseModel):
    _core_endpoint = "/dashboard/cluster"
    _model_name = "clusters"
    _pretty_name = "Clusters"

    name: str
    size: int | None = None


class StoryConflict(TaranisBaseModel):
    _core_endpoint = "connectors/conflicts/story-conflicts"
    _cache_timeout = 5
    _model_name = "story_conflicts"
    _pretty_name = "Story Conflicts"

    story_id: str
    existing_story: str
    incoming_story: str
    has_proposals: str | None = None


class NewsItemConflict(TaranisBaseModel):
    _core_endpoint = "/connectors/conflicts/news-items"
    _cache_timeout = 5
    _model_name = "news_item_conflict"
    _pretty_name = "News Item Conflicts"

    incoming_story_id: str
    news_item_id: str
    existing_story_id: str
    incoming_story: dict[str, Any]
    misp_address: str | None = None
