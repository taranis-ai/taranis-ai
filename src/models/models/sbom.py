"""Asset SBOM preview and inventory contracts shared by Core and the frontend."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from models.asset_intelligence import TriggerInput


SBOM_PARSER_VERSION = 3
SBOM_BATCH_SIZE = 100


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
    group: str = ""
    purl: str = ""
    suppliers: list[str] = Field(default_factory=list)
    cpes: list[str] = Field(default_factory=list)
    invalid_cpes: list[str] = Field(default_factory=list)
    occurrences: list[SbomOccurrence] = Field(default_factory=list)
    suggestions: list[TriggerSuggestion] = Field(default_factory=list)
    review_conflicts: list[str] = Field(default_factory=list)


class SbomFinding(BaseModel):
    identifier: str
    cve_id: str = ""
    records: list[dict[str, Any]]
    component_references: list[str]
    unresolved_references: list[str] = Field(default_factory=list)


class SbomSummary(BaseModel):
    spec_version: str
    serial_number: str = ""
    document_version: int
    generated_at: str = ""
    suggested_name: str = ""
    source_name: str = ""
    software_records: int
    excluded_files: int
    component_count: int
    components_with_cpes: int
    invalid_cpe_count: int
    parser_version: int = SBOM_PARSER_VERSION
    description: str = ""
    tools: dict | list = Field(default_factory=dict)
    external_references: list[dict[str, Any]] = Field(default_factory=list)
    vulnerabilities_supplied: bool = False
    finding_count: int = 0
    cve_count: int = 0
    affected_component_count: int = 0
    unresolved_reference_count: int = 0


class ParsedSbom(BaseModel):
    summary: SbomSummary
    components: list[SbomComponent]
    findings: list[SbomFinding]


class SbomComponentBatch(BaseModel):
    offset: int = Field(ge=0)
    items: list[SbomComponent] = Field(min_length=1, max_length=SBOM_BATCH_SIZE)


class SbomFindingBatch(BaseModel):
    offset: int = Field(ge=0)
    items: list[SbomFinding] = Field(min_length=1, max_length=SBOM_BATCH_SIZE)


class SbomUploadStatus(BaseModel):
    id: str
    filename: str
    status: Literal["QUEUED", "PROCESSING", "READY", "FAILED"]
    error: str = ""
    import_id: str | None = None
    target_asset_id: str | None = None
    components_received: int = 0
    findings_received: int = 0


class SbomComparison(BaseModel):
    asset_id: str
    asset_name: str
    expected_sha256: str | None
    components_added: int
    components_removed: int
    findings_added: int
    findings_removed: int
    cves_added: int
    cves_removed: int
    clears_findings: bool


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
    comparison: SbomComparison | None = None


class SbomCreateAsset(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_group_id: str = Field(min_length=1)
    description: str = Field(default="", max_length=10000)
    tags: list[str] = Field(default_factory=list)
    enable_software_matching: bool = True
    enable_cve_matching: bool = True


class SbomReplaceAsset(BaseModel):
    import_id: str
    expected_sha256: str | None
    enable_software_matching: bool = True
    enable_cve_matching: bool = True


class SbomCveMatching(BaseModel):
    enabled: bool


def component_identity(inventory: dict) -> tuple:
    """Identify an installed version consistently during parsing and replacement."""
    if inventory.get("purl"):
        return inventory["type"], inventory["purl"], inventory["version"]
    return (
        inventory["type"],
        inventory.get("group", ""),
        inventory["name"],
        inventory["version"],
        tuple(inventory.get("suppliers", [])),
        tuple(inventory["cpes"]),
        tuple(inventory.get("invalid_cpes", [])),
    )
