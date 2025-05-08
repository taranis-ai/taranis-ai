from pydantic import Field, AnyUrl
from typing import Literal
from datetime import datetime

from models.base import TaranisBaseModel
from models.types import TLPLevel, ItemType, COLLECTOR_TYPES
from models.assess import StoryTag


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    id: str
    name: str
    trigger: str
    next_run_time: str


class Address(TaranisBaseModel):
    city: str = ""
    country: str = ""
    street: str = ""
    zip: str = ""


class Organization(TaranisBaseModel):
    _core_endpoint = "/config/organizations"
    _model_name = "organization"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str = ""
    description: str | None = ""
    address: Address = Field(default_factory=Address)


class Permissions(TaranisBaseModel):
    _core_endpoint = "/config/permissions"
    _model_name = "permission"
    id: str
    name: str
    description: str


class ACL(TaranisBaseModel):
    _core_endpoint = "/config/acls"
    _model_name = "acl"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str = ""
    description: str | None = ""
    item_type: ItemType | None = None

    roles: list["Role"] = Field(default_factory=list["Role"])

    read_only: bool = True
    enabled: bool = True
    _pretty_name = "ACL"


class ParameterValue(TaranisBaseModel):
    _core_endpoint = "/config/parameter-values"
    _model_name = "parameter_value"
    id: int | None = None
    parameter: str = ""
    value: str | None = ""


class Worker(TaranisBaseModel):
    _core_endpoint = "/config/workers"
    _model_name = "worker"
    id: str
    name: str
    description: str | None = ""
    type: str | None = ""
    category: str | None = ""
    parameters: list["ParameterValue"] = Field(default_factory=list["ParameterValue"])


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    _model_name = "role"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str = ""
    description: str | None = ""
    permissions: list[str] = Field(default_factory=list[str])
    tlp_level: TLPLevel | None = None


class User(TaranisBaseModel):
    _core_endpoint = "/config/users"
    _model_name = "user"
    _search_fields = ["name", "username"]

    id: int | None = None
    name: str = ""
    organization: Organization | int | dict = Field(default_factory=dict)
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[Role] | list[int] | list[dict] = Field(default_factory=list[Role])
    username: str = ""
    password: str | None = None


class Dashboard(TaranisBaseModel):
    _core_endpoint = "/dashboard"
    _model_name = "dashboard"
    _pretty_name = "Dashboard"
    _cache_timeout = 30
    total_news_items: int | None = None
    total_products: int | None = None
    report_items_completed: int | None = None
    report_items_in_progress: int | None = None
    total_database_items: int | None = None
    latest_collected: str | None = None
    schedule_length: int | None = None
    conflict_count: int | None = None


class TrendingTag(TaranisBaseModel):
    _core_endpoint = "/dashboard/cluster"
    _model_name = "trending_tags"
    name: str
    tags: list[StoryTag] = Field(default_factory=list)
    size: int | None = None


class TrendingClusters(TaranisBaseModel):
    _core_endpoint = "/dashboard/trending-clusters"
    _model_name = "trending_clusters"
    _pretty_name = "Trending Clusters"
    root: list[TrendingTag] = Field(default_factory=list)


class TaranisConfig(TaranisBaseModel):
    default_collector_proxy: AnyUrl | Literal[""] = ""
    default_collector_interval: str = ""
    default_tlp_level: TLPLevel = TLPLevel.CLEAR


class Settings(TaranisBaseModel):
    _core_endpoint = "/admin/settings"
    _model_name = "settings"
    _pretty_name = "Settings"
    _cache_timeout = 30
    id: int = Field(default=1, frozen=True, exclude=True)
    settings: TaranisConfig | None = Field(default_factory=TaranisConfig)


class WordListEntry(TaranisBaseModel):
    value: str
    category: str | None = None
    description: str | None = None


class WordList(TaranisBaseModel):
    _core_endpoint = "/config/word-lists"
    _model_name = "word_list"
    _pretty_name = "Word List"
    _search_fields = ["name", "description"]

    id: int
    name: str
    description: str | None = None
    usage: int = 0
    link: str | None = None
    entries: list[WordListEntry] = Field(default_factory=list)


class OSINTSource(TaranisBaseModel):
    _core_endpoint = "/config/osint-sources"
    _model_name = "osint_source"
    _pretty_name = "OSINT Source"
    _search_fields = ["name", "description"]

    id: str
    name: str
    description: str = ""
    type: COLLECTOR_TYPES | Literal[""] = ""
    parameters: list[ParameterValue] = Field(default_factory=list)
    groups: list["OSINTSourceGroup"] = Field(default_factory=list)

    icon: str | None = None  # We'll assume it can be a base64 string
    state: int = -1
    last_collected: datetime | None = None
    last_attempted: datetime | None = None
    last_error_message: str | None = None


class OSINTSourceGroup(TaranisBaseModel):
    _core_endpoint = "/config/osint-source-groups"
    _model_name = "osint_source_group"
    _pretty_name = "OSINT Source Group"
    _search_fields = ["name", "description"]

    id: str
    name: str
    description: str = ""
    default: bool = False

    osint_sources: list[OSINTSource | str] = Field(default_factory=list)
    word_lists: list[WordList | str] = Field(default_factory=list)
