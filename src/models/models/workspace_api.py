"""User, dashboard, publishing, asset and settings HTTP operations."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, AnyUrl, BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, create_model

from models import admin, product
from models.api import (
    ApiEndpointModels,
    ErrorResponse,
    IdMessageResponse,
    ItemsResponse,
    MessageResponse,
    PageResponse,
    ResponseContract,
    download_response,
    json_response,
    partial_model,
)
from models.asset import Asset
from models.base import TaranisBaseModel
from models.config_api import ListQuery, QueueNotice, UserProfileResponse
from models.cti import CTIResponse
from models.dashboard import Cluster, Dashboard, PizzintStatus, TrendingCluster
from models.llm import LLMAPIConfig, LLMAPIFormat
from models.task import TaskResult
from models.user import LoginCredentials, ProfileSettings


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
    ApiEndpointModels(
        "POST",
        "/auth/login",
        {200: json_response(TokenResponse)},
        body=Annotated[LoginCredentials | ExternalLogin, Field(union_mode="left_to_right")] | None,
        request_media_types=("application/json", "application/x-www-form-urlencoded", "multipart/form-data"),
    ),
    ApiEndpointModels("GET", "/users/", {200: json_response(UserProfileResponse)}),
    ApiEndpointModels("GET", "/users/profile", {200: json_response(ProfileSettings)}),
    *(
        ApiEndpointModels(
            method,
            "/users/profile",
            {200: json_response(ProfileUpdated)},
            body=PROFILE_UPDATE,
        )
        for method in ("POST", "PUT")
    ),
    ApiEndpointModels("GET", "/dashboard", {200: json_response(ItemsResponse[Dashboard])}),
    ApiEndpointModels("GET", "/dashboard/pizzint", {200: json_response(PizzintStatus)}),
    ApiEndpointModels("GET", "/dashboard/cluster-names", {200: json_response(ItemsResponse[str])}),
    ApiEndpointModels("GET", "/dashboard/trending-clusters", {200: json_response(ItemsResponse[TrendingCluster])}, query=ClusterQuery),
    ApiEndpointModels("GET", "/dashboard/story-clusters", {200: json_response(list[StoryCluster])}, query=ClusterQuery),
    ApiEndpointModels("GET", "/dashboard/cluster/{tag_type}", {200: json_response(PageResponse[Cluster])}, query=ClusterQuery),
    ApiEndpointModels("DELETE", "/dashboard/delete-tag/{tag_name}", {200: json_response(MessageResponse)}),
    ApiEndpointModels(
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
            ApiEndpointModels("GET", path, {200: json_response(PageResponse[response_model])}, query=AssetQuery),
            ApiEndpointModels("POST", path, {201: json_response(IdMessageResponse)}, body=input_model),
            ApiEndpointModels("PUT", path, {}, body=partial_model(input_model)),
            ApiEndpointModels("DELETE", path, {}),
            ApiEndpointModels("GET", f"{path}/{{{identifier}}}", {200: json_response(response_model)}, query=AssetQuery),
            ApiEndpointModels(
                "PUT",
                f"{path}/{{{identifier}}}",
                {200: json_response(MessageResponse | IdMessageResponse), 201: json_response(IdMessageResponse)},
                body=partial_model(input_model),
            ),
            ApiEndpointModels("DELETE", f"{path}/{{{identifier}}}", {200: json_response(MessageResponse | IdMessageResponse)}),
        )
    ),
    ApiEndpointModels("GET", "/assets/cti", {200: json_response(CTIResponse)}),
    ApiEndpointModels("GET", "/assets/{asset_id}/cti", {200: json_response(CTIResponse)}),
    ApiEndpointModels(
        "PUT",
        "/assets/{asset_id}/vulnerabilities/{vulnerability_id}",
        {200: json_response(MessageResponse), 400: json_response(ErrorResponse | MessageResponse)},
        body=SolvedRequest,
    ),
    ApiEndpointModels("GET", "/publish/product-types", {200: json_response(ItemsResponse[admin.ProductType])}),
    ApiEndpointModels("GET", "/publish/product-choices", {200: json_response(ItemsResponse[product.ProductChoice])}),
    ApiEndpointModels(
        "GET",
        "/publish/product-type-choices",
        {200: json_response(ItemsResponse[product.ProductTypeChoice])},
        query=ProductTypeQuery,
        repeated_query=("report_ids",),
    ),
    ApiEndpointModels("GET", "/publish/product-metadata/{product_id}", {200: json_response(PRODUCT_RESPONSE)}),
    ApiEndpointModels("GET", "/publish/publisher-presets", {200: json_response(PageResponse[product.PublisherPreset])}, query=ListQuery),
    ApiEndpointModels("GET", "/publish/publisher-presets/{preset_id}", {200: json_response(product.PublisherPreset)}, query=ListQuery),
    ApiEndpointModels("GET", "/publish/products", {200: json_response(PageResponse[PRODUCT_RESPONSE])}, query=ProductQuery),
    ApiEndpointModels("GET", "/publish/products/{product_id}", {200: json_response(PRODUCT_RESPONSE)}),
    ApiEndpointModels("POST", "/publish/products", {201: json_response(ProductWritten)}, body=ProductInput),
    ApiEndpointModels("PUT", "/publish/products/{product_id}", {200: json_response(ProductWritten)}, body=partial_model(ProductInput)),
    ApiEndpointModels("DELETE", "/publish/products/{product_id}", {200: json_response(MessageResponse)}),
    ApiEndpointModels("POST", "/publish/products/{product_id}/render", {200: json_response(QueueNotice)}),
    ApiEndpointModels(
        "GET",
        "/publish/products/{product_id}/render",
        {200: download_response(json_body=RenderFailure), 206: download_response(), 304: ResponseContract(None, media_type=None)},
    ),
    ApiEndpointModels("POST", "/publish/products/{product_id}/publishers/{publisher_id}", {200: json_response(QueueNotice)}),
    ApiEndpointModels("GET", "/publish/products/auto-render/{report_item_id}", {200: json_response(ProductList)}),
    *(
        ApiEndpointModels("POST", f"/settings/{action}", {200: json_response(MessageResponse)})
        for action in ("delete-tags", "delete-stories", "clear-queues")
    ),
    *(ApiEndpointModels("POST", f"/settings/{action}", {}) for action in ("ungroup-stories", "reset-database")),
    ApiEndpointModels("POST", "/settings/rebuild-story-search-vectors", {200: json_response(RebuildResponse)}),
    ApiEndpointModels("GET", "/settings/export-stories", {200: download_response("application/json")}, query=admin.ExportStoriesQuery),
    ApiEndpointModels("GET", "/settings/settings", {200: json_response(SettingsResponse)}),
    *(
        ApiEndpointModels(
            method,
            "/settings/settings",
            {200: json_response(SettingsUpdated)},
            body=SETTINGS_INPUT,
        )
        for method in ("PUT", "PATCH", "POST")
    ),
    *(
        ApiEndpointModels(
            "POST",
            path,
            {200: json_response(IdMessageResponse)},
            body=partial_model(LLMWrite),
        )
        for path in ("/settings/llm-endpoints", "/settings/llm-endpoints/{endpoint_id}")
    ),
    ApiEndpointModels("POST", "/settings/llm-endpoints/{endpoint_id}/delete", {200: json_response(IdMessageResponse)}),
    ApiEndpointModels(
        "POST",
        "/admin/cache/invalidate",
        {200: json_response(CacheResponse)},
        body=CacheRequest,
    ),
)
