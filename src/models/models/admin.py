from pydantic import Field, AnyUrl
from functools import cached_property
from typing import Literal, Any
from datetime import datetime

from models.base import TaranisBaseModel
from models.types import (
    TLPLevel,
    ItemType,
    COLLECTOR_TYPES,
    CONNECTOR_TYPES,
    WORKER_TYPES,
    WORKER_CATEGORY,
    PRESENTER_TYPES,
    AttributeType,
    BOT_TYPES,
    PUBLISHER_TYPES,
)


class Job(TaranisBaseModel):
    _core_endpoint = "/config/schedule"
    _model_name = "job"
    _pretty_name = "Scheduler"

    id: str | None = None
    name: str
    trigger: str | None = None
    kwargs: str | None = None
    next_run_time: str | None = None


class TaskResult(TaranisBaseModel):
    _core_endpoint = "/config/task-results"
    _model_name = "task_result"
    _pretty_name = "Task Result"

    id: str | None = None
    result: Any | None = None
    status: str | None = None
    last_change: datetime | None = None
    last_success: datetime | None = None

    def __eq__(self, other: object) -> bool:
        return self.status == (other.status if isinstance(other, TaskResult) else other)

    def __lt__(self, other: object) -> bool:
        other_status = other.status if isinstance(other, TaskResult) else other

        if self.status is None:
            return other_status is not None
        return False if other_status is None else str(self.status) < str(other_status)


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


class Permission(TaranisBaseModel):
    _core_endpoint = "/config/permissions"
    _model_name = "permission"
    id: str | None = None
    name: str
    description: str = ""


class ACL(TaranisBaseModel):
    _core_endpoint = "/config/acls"
    _model_name = "acl"
    _search_fields = ["name", "description"]
    _pretty_name = "ACL"

    id: int | None = None
    name: str = ""
    description: str | None = ""
    item_type: ItemType | None = None
    item_id: str | None = None

    roles: list[int] = Field(default_factory=list)

    read_only: bool = True
    enabled: bool = True


class ParameterValue(TaranisBaseModel):
    _core_endpoint = "/config/parameter-values"
    _model_name = "parameter_value"
    id: int | None = None
    parameter: str = ""
    value: str | None = ""


class Worker(TaranisBaseModel):
    _core_endpoint = "/config/worker-types"
    _model_name = "worker_type"
    _search_fields = ["name", "description"]
    _pretty_name = "Worker Type"

    id: str | None = None
    name: str
    description: str | None = ""
    type: WORKER_TYPES
    category: WORKER_CATEGORY
    parameters: dict[str, str] = Field(default_factory=dict)


class Role(TaranisBaseModel):
    _core_endpoint = "/config/roles"
    _model_name = "role"
    _search_fields = ["name", "description"]
    _pretty_name = "Role"

    id: int | None = None
    name: str = ""
    description: str | None = ""
    permissions: list[str] = Field(default_factory=list)
    tlp_level: TLPLevel | None = None


class User(TaranisBaseModel):
    _core_endpoint = "/config/users"
    _model_name = "user"
    _search_fields = ["name", "username"]

    id: int | None = None
    name: str
    organization: dict | int
    permissions: list[str] | None = None
    profile: dict | None = None
    roles: list[int] | list[dict] = Field(default_factory=list)
    username: str = ""
    password: str | None = Field(default=None, exclude=True)


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
    settings: TaranisConfig = Field(default_factory=TaranisConfig)


class WordListEntry(TaranisBaseModel):
    value: str
    category: str | None = None
    description: str | None = None


class WordList(TaranisBaseModel):
    _core_endpoint = "/config/word-lists"
    _model_name = "word_list"
    _pretty_name = "Word List"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str
    description: str | None = ""
    usage: list[str] = Field(default_factory=list)
    link: str = ""
    entries: list[WordListEntry] | None = Field(default_factory=list)


class OSINTSource(TaranisBaseModel):
    _core_endpoint = "/config/osint-sources"
    _model_name = "osint_source"
    _pretty_name = "OSINT Source"

    id: str | None = None
    name: str
    description: str = ""
    type: COLLECTOR_TYPES | None = None
    parameters: dict[str, str] | None = Field(default_factory=dict)

    icon: str | None = None
    enabled: bool | None = True
    status: TaskResult | None = None

    @cached_property
    def search_field(self) -> str:
        search = f"{self.name} {self.description} "
        if self.parameters:
            search += " ".join(self.parameters.values())
        return search


class OSINTSourceGroup(TaranisBaseModel):
    _core_endpoint = "/config/osint-source-groups"
    _model_name = "osint_source_group"
    _pretty_name = "OSINT Source Group"
    _search_fields = ["name", "description"]

    id: str | None = None
    name: str
    description: str = ""
    default: bool = False

    osint_sources: list[str] = Field(default_factory=list)
    word_lists: list[int] = Field(default_factory=list)


class ProductParameterValue(TaranisBaseModel):
    TEMPLATE_PATH: str | None = None


class ProductType(TaranisBaseModel):
    _core_endpoint = "/config/product-types"
    _model_name = "product_type"
    _pretty_name = "Product Type"
    _search_fields = ["title", "description"]

    id: int | None = None
    title: str
    description: str = ""
    type: PRESENTER_TYPES
    parameters: ProductParameterValue = Field(default_factory=ProductParameterValue)
    report_types: list[int] = Field(default_factory=list)
    status: TaskResult | None = None


class PublisherPreset(TaranisBaseModel):
    _core_endpoint = "/config/publisher-presets"
    _model_name = "publisher_preset"
    _pretty_name = "Publisher Preset"
    _search_fields = ["name", "description"]

    id: str | None = None
    name: str
    type: PUBLISHER_TYPES
    description: str | None = ""
    parameters: dict[str, str] | None = Field(default_factory=dict)
    status: TaskResult | None = None


class ReportItemAttribute(TaranisBaseModel):
    id: int | None = None
    attribute: dict[str, str] | None = None
    attribute_id: int | None = None
    attribute_group_id: int | None = None
    title: str | None = None
    description: str | None = None
    index: int | None = None
    required: bool | None = None
    type: str | None = None


class ReportItemAttributeGroup(TaranisBaseModel):
    id: int | None = None
    title: str | None = None
    description: str | None = None
    index: int | None = None
    attribute_group_items: list[ReportItemAttribute] = Field(default_factory=list)


class ReportItemType(TaranisBaseModel):
    _core_endpoint = "/config/report-item-types"
    _model_name = "report_item_type"
    _pretty_name = "Report Item Type"
    _search_fields = ["title", "description"]

    id: int | None = None
    title: str
    description: str = ""
    attribute_groups: list[ReportItemAttributeGroup] | None = Field(default_factory=list)


class Template(TaranisBaseModel):
    _core_endpoint = "/config/templates"
    _model_name = "template"
    _pretty_name = "Template"

    id: str
    content: str | None = None
    validation_status: dict | None = None


class AttributeEnum(TaranisBaseModel):
    id: int | None = None
    index: int | None = None
    value: str | None = None
    description: str | None = None
    imported: bool | None = None
    attribute_id: int | None = None


class Attribute(TaranisBaseModel):
    _core_endpoint = "/config/attributes"
    _model_name = "attribute"
    _pretty_name = "Attribute"
    _search_fields = ["name", "description"]

    id: int | None = None
    name: str
    description: str = ""
    type: AttributeType
    default_value: str = ""
    attribute_enums: list[AttributeEnum] = Field(default_factory=list)


class Bot(TaranisBaseModel):
    _core_endpoint = "/config/bots"
    _model_name = "bot"
    _pretty_name = "Bot"
    _search_fields = ["name", "description"]

    id: str | None = None
    name: str
    description: str = ""
    type: BOT_TYPES
    index: int | None = None
    parameters: dict[str, str] | None = Field(default_factory=dict)
    status: TaskResult | None = None


class Connector(TaranisBaseModel):
    _core_endpoint = "/config/connectors"
    _model_name = "connector"
    _pretty_name = "Connector"
    _search_fields = ["name", "description"]

    id: str | None = None
    name: str
    description: str = ""
    type: CONNECTOR_TYPES = Field(default=CONNECTOR_TYPES.MISP_CONNECTOR)
    index: int | None = None
    parameters: dict[str, str] = Field(default_factory=dict)
    icon: str | None = None
    status: TaskResult | None = None


class WorkerParameterValue(TaranisBaseModel):
    name: str
    label: str | None = None
    parent: Literal["parameters"] = "parameters"
    type: str | None = None
    rules: list[str] = Field(default_factory=list)


class WorkerParameter(TaranisBaseModel):
    _core_endpoint = "/config/worker-parameters"
    _model_name = "worker_parameter"
    _pretty_name = "Worker Parameter"

    id: str
    parameters: list[WorkerParameterValue]
