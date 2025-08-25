from pydantic import Field
from datetime import datetime

from models.base import TaranisBaseModel
from models.assess import StoryTag


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
    worker_status: dict[str, dict[str, int]] | None = None


class TrendingCluster(TaranisBaseModel):
    _core_endpoint = "/dashboard/trending-clusters"
    _model_name = "trending_clusters"
    _pretty_name = "Trending Clusters"

    name: str
    tags: list[StoryTag] = Field(default_factory=list)
    size: int | None = None
