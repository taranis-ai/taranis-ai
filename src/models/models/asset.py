from models.base import TaranisBaseModel


class Asset(TaranisBaseModel):
    _core_endpoint = "/assets"
    _model_name = "asset"
    _search_fields = ["name"]
    _pretty_name = "Assets"

    id: str | None = None
    name: str | None = ""
    description: str | None = ""
