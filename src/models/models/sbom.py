"""Asset SBOM preview and inventory contracts shared by Core and the frontend."""

from pydantic import BaseModel, Field

from models.asset_intelligence import TriggerInput


class TriggerSuggestion(TriggerInput):
    sources: list[str]


class SbomOccurrence(BaseModel):
    reference: str
    locations: list[str] = Field(default_factory=list)


class SbomComponent(BaseModel):
    id: str = ""
    name: str
    version: str = ""
    type: str
    purl: str = ""
    suppliers: list[str] = Field(default_factory=list)
    cpes: list[str] = Field(default_factory=list)
    invalid_cpes: list[str] = Field(default_factory=list)
    occurrences: list[SbomOccurrence] = Field(default_factory=list)
    suggestions: list[TriggerSuggestion] = Field(default_factory=list)


class SbomSummary(BaseModel):
    spec_version: str
    serial_number: str = ""
    document_version: int
    generated_at: str = ""
    suggested_name: str = ""
    software_records: int
    excluded_files: int
    component_count: int
    components_with_cpes: int
    invalid_cpe_count: int


class SbomInventory(BaseModel):
    id: str
    asset_id: str | None = None
    filename: str
    sha256: str
    imported_at: str
    summary: SbomSummary
    components: list[SbomComponent]
    page: int
    pages: int


class SbomCreateAsset(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_group_id: str = Field(min_length=1)
    description: str = Field(default="", max_length=10000)
