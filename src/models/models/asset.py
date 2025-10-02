from pydantic import Field
from models.base import TaranisBaseModel


class Asset(TaranisBaseModel):
    _core_endpoint = "/assets"
    _model_name = "asset"
    _search_fields = ["name"]
    _pretty_name = "Assets"

    id: int | None = None
    name: str | None = ""
    description: str | None = ""
    serial: str | None = ""
    asset_group_id: str | None = None
    asset_cpes: list[int] = Field(default_factory=list)
    vulnerabilities: list[int] = Field(default_factory=list)
    vulnerabilities_count: int | None = None
