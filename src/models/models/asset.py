from pydantic import Field

from models.base import TaranisBaseModel
from models.cti import CanonicalIOCType


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
    asset_cpes: list[str] = Field(default_factory=list)
    asset_observables: list[AssetObservable] = Field(default_factory=list)
    vulnerabilities: list[str] = Field(default_factory=list)
    vulnerabilities_count: int | None = None
