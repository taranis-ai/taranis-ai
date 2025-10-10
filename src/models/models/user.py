from pydantic import Field
from typing import Any

from models.base import TaranisBaseModel


class ProfileSettingsDashboard(TaranisBaseModel):
    show_trending_clusters: bool = True
    show_charts: bool = True
    trending_cluster_days: int = 7
    trending_cluster_filter: list[Any] = Field(default_factory=list)


class ProfileSettings(TaranisBaseModel):
    _core_endpoint = "/users/profile"
    _model_name = "profile_settings"

    dark_theme: bool = False
    compact_view: bool = False
    show_charts: bool = False
    infinite_scroll: bool = True
    advanced_story_options: bool = True
    language: str = "en"
    hotkeys: dict[str, Any] = Field(default_factory=dict)
    split_view: bool = False
    end_of_shift: str | dict = None
    highlight: bool = True
    dashboard: ProfileSettingsDashboard = Field(default_factory=ProfileSettingsDashboard)


class UserProfile(TaranisBaseModel):
    _core_endpoint = "/users"
    _model_name = "user_profile"
    _search_fields = ["name", "username"]

    id: int | None = None
    username: str = ""
    name: str
    organization: dict[str, Any] | None = None
    profile: ProfileSettings = Field(default_factory=ProfileSettings)
    permissions: list[str] | None = Field(default_factory=list)
    roles: list[dict[str, Any]] | None = Field(default_factory=list)
