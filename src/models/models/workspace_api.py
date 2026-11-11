"""User, dashboard, publishing, asset and settings HTTP operations."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, AnyUrl, BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, create_model, model_validator

from models import admin, product
from models.api import (
    ErrorResponse,
    IdMessageResponse,
    ItemsResponse,
    MessageResponse,
    OperationContract,
    PageResponse,
    ResponseContract,
    download_response,
    json_response,
    partial_model,
)
from models.asset import Asset
from models.base import TaranisBaseModel
from models.config_api import ListQuery, QueueNotice
from models.cti import CTIResponse
from models.dashboard import Cluster, Dashboard, PizzintStatus, TrendingCluster
from models.llm import LLMAPIConfig, LLMAPIFormat
from models.task import TaskResult
from models.user import LoginCredentials, ProfileSettings, UserProfileResponse


class RenderFailure(BaseModel):
    error: str | TaskResult


class ExternalLogin(BaseModel):
    username: str
    roles: str
    name: str
    organization: str


class TokenResponse(BaseModel):
    access_token: str


class ProfileUpdated(IdMessageResponse):
    user_profile: ProfileSettings


class ClusterQuery(ListQuery):
    days: int | None = None

    @model_validator(mode="after")
    def validate_runtime_bounds(self):
        if self.days is not None:
            try:
                datetime.now(UTC) - timedelta(days=self.days)
            except OverflowError:
                raise ValueError("Days exceed the supported date range") from None
        limit = min(self.limit, 100)
        offset = min((self.page - 1) * limit, (2**31) - 1)
        if limit < -(2**63) or offset < -(2**63):
            raise ValueError("Pagination exceeds the supported integer range")
        return self


class StoryCluster(BaseModel):
    name: str
    size: int
    published: list[datetime]


class BuildInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    build_date: datetime


class AssetGroupInput(TaranisBaseModel):
    id: str | None = None
    name: str
    description: str | None = ""


class AssetGroupResponse(AssetGroupInput):
    organization_id: str | None


class AssetQuery(ListQuery):
    vulnerable: bool | None = None
    group: str | None = None


class SolvedRequest(BaseModel):
    solved: bool


class ProductInput(TaranisBaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)
    id: str | None = None
    title: str
    description: str | None = ""
    product_type_id: str
    report_items: list[str] | None = None
    auto_publish: bool | None = False
    default_publisher: str | None = None


class ProductWritten(IdMessageResponse):
    product: product.Product


class ProductList(BaseModel):
    products: list[product.Product]


class ProductQuery(ListQuery):
    range: str | None = None


class ProductTypeQuery(BaseModel):
    report_ids: list[str] = Field(default_factory=list)


def unchanged_proxy_url(value: str) -> str:
    if value:
        TypeAdapter(AnyUrl).validate_python(value)
    return value


SETTINGS_VALUES_INPUT = create_model(
    "SettingsValuesInput",
    __base__=admin.TaranisConfig,
    default_collector_proxy=(Annotated[str, AfterValidator(unchanged_proxy_url)], ""),
)
SETTINGS_INPUT = create_model("SettingsInput", __base__=TaranisBaseModel, settings=(SETTINGS_VALUES_INPUT, ...))
SETTINGS_ERRORS = {
    "settings": "settings must be a JSON object",
    "settings.default_timezone": "Invalid timezone",
    "settings.default_bot_lookback_days": "Invalid bot lookback setting",
    "settings.rss_collector_max_entries": "Invalid RSS collector entry limit",
    "settings.collection_group_threshold": "Collection threshold must be 1–100 and lookback days must be 1–36500",
    "settings.collection_lookback_days": "Collection threshold must be 1–100 and lookback days must be 1–36500",
    "settings.onboarding_enabled": "Invalid onboarding setting",
    "settings.chat_max_stories": "Maximum stories must be between 1 and 20",
}


class SettingsUpdated(BaseModel):
    message: str
    settings: admin.TaranisConfig


class SettingsResponse(BaseModel):
    items: list[admin.Settings]
    links: dict[str, str] = Field(alias="_links")


class RebuildResponse(MessageResponse):
    updated: int


class CacheRequest(BaseModel):
    mode: Literal["all", "model", "scope"]
    model: str | None = None
    scope: str | None = None
    object_id: str | None = None


class CacheResponse(MessageResponse):
    deleted: int
    mode: Literal["all", "model", "scope"]
    model: str | None = None
    scope: str | None = None


class LLMWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    enabled: bool = True
    api_formats: dict[LLMAPIFormat, LLMAPIConfig] = Field(min_length=1)
    api_format: LLMAPIFormat = "responses"
    model: str = ""
    processing_mode: Literal["realtime", "openrouter_batch"] = "realtime"
    api_key: str = Field(default="", repr=False)
    api_key_clear: bool | str = False
    timeout: int = Field(default=120, gt=0)


ASSET_RESPONSE = create_model("AssetResponse", __base__=Asset, id=(str, ...))
PRODUCT_RESPONSE = create_model("ProductResponse", __base__=product.Product, id=(str, ...))
PROFILE_UPDATE = partial_model(ProfileSettings)


OPERATIONS = (
    OperationContract(
        "GET",
        "/reports/{product_id}",
        {200: download_response(), 206: download_response(), 304: ResponseContract(None, media_type=None)},
        api_path=False,
    ),
    OperationContract(
        "POST",
        "/auth/login",
        {200: json_response(TokenResponse)},
        body=TypeAdapter(Annotated[LoginCredentials | ExternalLogin, Field(union_mode="left_to_right")] | None),
        request_media_types=("application/json", "application/x-www-form-urlencoded", "multipart/form-data"),
        validation_error_message="Missing username or password",
    ),
    OperationContract("GET", "/users/", {200: json_response(UserProfileResponse)}),
    OperationContract("GET", "/users/profile", {200: json_response(ProfileSettings)}),
    *(
        OperationContract(
            method,
            "/users/profile",
            {200: json_response(ProfileUpdated)},
            body=TypeAdapter(PROFILE_UPDATE),
            invalid_request_message="Invalid profile settings",
        )
        for method in ("POST", "PUT")
    ),
    OperationContract("GET", "/dashboard", {200: json_response(ItemsResponse[Dashboard])}),
    OperationContract("GET", "/dashboard/pizzint", {200: json_response(PizzintStatus)}),
    OperationContract("GET", "/dashboard/cluster-names", {200: json_response(ItemsResponse[str])}),
    OperationContract("GET", "/dashboard/trending-clusters", {200: json_response(ItemsResponse[TrendingCluster])}, query=ClusterQuery),
    OperationContract("GET", "/dashboard/story-clusters", {200: json_response(list[StoryCluster])}, query=ClusterQuery),
    OperationContract("GET", "/dashboard/cluster/{tag_type}", {200: json_response(PageResponse[Cluster])}, query=ClusterQuery),
    OperationContract("DELETE", "/dashboard/delete-tag/{tag_name}", {200: json_response(MessageResponse)}),
    OperationContract(
        "GET",
        "/dashboard/build-info",
        {200: json_response(Annotated[BuildInfo, BeforeValidator(TypeAdapter(dict[str, str]).validate_python)])},
    ),
    *(
        operation
        for path, identifier, input_model, response_model in (
            ("/assets", "asset_id", Asset, ASSET_RESPONSE),
            ("/asset-groups", "group_id", AssetGroupInput, AssetGroupResponse),
        )
        for operation in (
            OperationContract("GET", path, {200: json_response(PageResponse[response_model])}, query=AssetQuery),
            OperationContract("POST", path, {201: json_response(IdMessageResponse)}, body=TypeAdapter(input_model)),
            OperationContract("PUT", path, {}, body=TypeAdapter(partial_model(input_model))),
            OperationContract("DELETE", path, {}),
            OperationContract("GET", f"{path}/{{{identifier}}}", {200: json_response(response_model)}, query=AssetQuery),
            OperationContract(
                "PUT",
                f"{path}/{{{identifier}}}",
                {200: json_response(MessageResponse | IdMessageResponse), 201: json_response(IdMessageResponse)},
                body=TypeAdapter(partial_model(input_model)),
            ),
            OperationContract("DELETE", f"{path}/{{{identifier}}}", {200: json_response(MessageResponse | IdMessageResponse)}),
        )
    ),
    OperationContract("GET", "/assets/cti", {200: json_response(CTIResponse)}),
    OperationContract("GET", "/assets/{asset_id}/cti", {200: json_response(CTIResponse)}),
    OperationContract(
        "PUT",
        "/assets/{asset_id}/vulnerabilities/{vulnerability_id}",
        {200: json_response(MessageResponse), 400: json_response(ErrorResponse | MessageResponse)},
        body=TypeAdapter(SolvedRequest),
    ),
    OperationContract("GET", "/publish/product-types", {200: json_response(ItemsResponse[admin.ProductType])}),
    OperationContract("GET", "/publish/product-choices", {200: json_response(ItemsResponse[product.ProductChoice])}),
    OperationContract(
        "GET",
        "/publish/product-type-choices",
        {200: json_response(ItemsResponse[product.ProductTypeChoice])},
        query=ProductTypeQuery,
        repeated_query=("report_ids",),
    ),
    OperationContract("GET", "/publish/product-metadata/{product_id}", {200: json_response(PRODUCT_RESPONSE)}),
    OperationContract("GET", "/publish/publisher-presets", {200: json_response(PageResponse[product.PublisherPreset])}, query=ListQuery),
    OperationContract("GET", "/publish/publisher-presets/{preset_id}", {200: json_response(product.PublisherPreset)}, query=ListQuery),
    OperationContract("GET", "/publish/products", {200: json_response(PageResponse[PRODUCT_RESPONSE])}, query=ProductQuery),
    OperationContract("GET", "/publish/products/{product_id}", {200: json_response(PRODUCT_RESPONSE)}),
    OperationContract("POST", "/publish/products", {201: json_response(ProductWritten)}, body=TypeAdapter(ProductInput)),
    OperationContract(
        "PUT", "/publish/products/{product_id}", {200: json_response(ProductWritten)}, body=TypeAdapter(partial_model(ProductInput))
    ),
    OperationContract("DELETE", "/publish/products/{product_id}", {200: json_response(MessageResponse)}),
    OperationContract("POST", "/publish/products/{product_id}/render", {200: json_response(QueueNotice)}),
    OperationContract(
        "GET",
        "/publish/products/{product_id}/render",
        {200: download_response(json_body=RenderFailure), 206: download_response(), 304: ResponseContract(None, media_type=None)},
    ),
    OperationContract("POST", "/publish/products/{product_id}/publishers/{publisher_id}", {200: json_response(QueueNotice)}),
    OperationContract("GET", "/publish/products/auto-render/{report_item_id}", {200: json_response(ProductList)}),
    *(
        OperationContract("POST", f"/settings/{action}", {200: json_response(MessageResponse)})
        for action in ("delete-tags", "delete-stories", "clear-queues")
    ),
    *(OperationContract("POST", f"/settings/{action}", {}) for action in ("ungroup-stories", "reset-database")),
    OperationContract("POST", "/settings/rebuild-story-search-vectors", {200: json_response(RebuildResponse)}),
    OperationContract("GET", "/settings/export-stories", {200: download_response("application/json")}, query=admin.ExportStoriesQuery),
    OperationContract("GET", "/settings/settings", {200: json_response(SettingsResponse)}),
    *(
        OperationContract(
            method,
            "/settings/settings",
            {200: json_response(SettingsUpdated)},
            body=TypeAdapter(SETTINGS_INPUT),
            field_error_messages=SETTINGS_ERRORS,
        )
        for method in ("PUT", "PATCH", "POST")
    ),
    *(
        OperationContract(
            "POST",
            path,
            {200: json_response(IdMessageResponse)},
            body=TypeAdapter(partial_model(LLMWrite)),
            validation_error_message="Invalid LLM endpoint",
        )
        for path in ("/settings/llm-endpoints", "/settings/llm-endpoints/{endpoint_id}")
    ),
    OperationContract("POST", "/settings/llm-endpoints/{endpoint_id}/delete", {200: json_response(IdMessageResponse)}),
    OperationContract(
        "POST",
        "/admin/cache/invalidate",
        {200: json_response(CacheResponse)},
        body=TypeAdapter(CacheRequest),
        validation_error_message="Invalid mode",
    ),
    OperationContract(
        "GET",
        "/static/default_word_lists.json",
        {200: download_response(), 206: download_response(), 304: ResponseContract(None, media_type=None)},
    ),
    OperationContract(
        "GET", "/static/openapi3_1.yaml", {200: download_response(), 206: download_response(), 304: ResponseContract(None, media_type=None)}
    ),
)
