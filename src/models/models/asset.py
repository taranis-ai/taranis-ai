from pydantic import Field

from models.base import TaranisBaseModel
from models.cti import CanonicalIOCType


def normalize_asset_tags(values: list[str]) -> list[str]:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError("Asset tags must be a list of strings")
    return sorted({value.strip().lower() for value in values if value.strip()})


class AssetObservable(TaranisBaseModel):
    id: str | None = None
    ioc_type: CanonicalIOCType
    value: str


class Asset(TaranisBaseModel):
    _core_endpoint = "/assets"
    _model_name = "asset"
    _pretty_name = "Assets"

    id: str | None = None
    name: str | None = ""
    description: str | None = ""
    serial: str | None = ""
    asset_group_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    asset_cpes: list[str] = Field(default_factory=list)
    asset_observables: list[AssetObservable] = Field(default_factory=list)
    vulnerabilities: list[str] = Field(default_factory=list)
    vulnerabilities_count: int | None = None


class AssetGroup(TaranisBaseModel):
    _core_endpoint = "/asset-groups"
    _model_name = "asset_group"
    _pretty_name = "Asset groups"

    id: str
    name: str
