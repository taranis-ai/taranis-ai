from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from models.base import TaranisBaseModel


ONBOARDING_COMPLETED_STATUS = "completed"
ONBOARDING_DISMISSED_STATUS = "dismissed"
ONBOARDING_SCOPE_GLOBAL = "global"
ONBOARDING_SCOPE_USER = "user"
ADMIN_WELCOME_TOUR_ID = "admin_welcome_v1"
ADMIN_ADVANCED_TOUR_ID = "admin_advanced_v1"
USER_PRODUCT_OVERVIEW_TASK_ID = "user_product_overview_v1"


class ProfileSettingsDashboard(TaranisBaseModel):
    show_trending_clusters: bool = True
    show_charts: bool = True
    trending_cluster_days: int = 7
    trending_cluster_filter: list[Any] = Field(default_factory=list)


class OnboardingTask(TaranisBaseModel):
    id: str
    scope: Literal["global", "user"]


class AssessSavedFilter(TaranisBaseModel):
    id: str
    name: str
    filters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ProfileSettings(TaranisBaseModel):
    _core_endpoint = "/users/profile"
    _model_name = "profile_settings"

    dark_theme: bool = False
    compact_view: bool = False
    show_charts: bool = False
    infinite_scroll: bool = True
    advanced_story_options: bool = False
    language: str = "en"
    timezone: str | None = None
    hotkeys: dict[str, Any] = Field(default_factory=dict)
    split_view: bool = False
    end_of_shift: str | None = None
    highlight: bool = False
    assess_saved_filters: list[AssessSavedFilter] = Field(default_factory=list)
    onboarding_tasks: dict[str, str] = Field(default_factory=dict)
    dashboard: ProfileSettingsDashboard = Field(default_factory=ProfileSettingsDashboard)

    @field_validator("timezone", mode="after")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        timezone_name = (value or "").strip()
        if not timezone_name:
            return None
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Invalid timezone: {timezone_name}") from exc
        return timezone_name


class UserProfile(TaranisBaseModel):
    _core_endpoint = "/users"
    _model_name = "user_profile"

    id: str | None = None
    username: str = ""
    name: str
    last_login: datetime | None = None
    organization: dict[str, Any] | None = None
    profile: ProfileSettings = Field(default_factory=ProfileSettings)
    effective_timezone: str = "UTC"
    permissions: list[str] | None = Field(default_factory=list)
    roles: list[dict[str, Any]] | None = Field(default_factory=list)
    pending_onboarding_tasks: list[OnboardingTask] = Field(default_factory=list)
