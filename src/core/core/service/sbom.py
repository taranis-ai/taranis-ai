"""Normalize CycloneDX software inventory without treating file records as packages."""

import json
import re
from functools import lru_cache
from typing import Any, Literal

from cpe.cpe2_3_fs import CPE2_3_FS
from cpe.cpe2_3_uri import CPE2_3_URI
from models.cti import normalize_ioc_value
from models.sbom import ParsedSbom, SbomComponent, SbomFinding, SbomOccurrence, SbomSummary
from packageurl import PackageURL
from pydantic import BaseModel, Field, ValidationError


MAX_COMPONENTS = 100_000
MAX_NESTING = 64
MAX_FINDINGS = 100_000
MAX_FINDING_REFERENCES = 1_000_000


class SbomValidationError(ValueError):
    """Messages are curated for display to the importing analyst."""

    def __init__(self, public_message: str):
        super().__init__(public_message)
        self.public_message = public_message


class CycloneDxProperty(BaseModel):
    name: str
    value: str


class CycloneDxComponent(BaseModel):
    type: Literal[
        "application",
        "framework",
        "library",
        "container",
        "platform",
        "operating-system",
        "device",
        "device-driver",
        "firmware",
        "file",
        "machine-learning-model",
        "data",
        "cryptographic-asset",
    ]
    name: str = Field(min_length=1)
    version: str = ""
    reference: str = Field(default="", alias="bom-ref")
    group: str = ""
    purl: str = ""
    cpe: str = ""
    supplier: dict[str, Any] = Field(default_factory=dict)
    publisher: str = ""
    properties: list[CycloneDxProperty] = Field(default_factory=list)


class CycloneDxDocument(BaseModel):
    bomFormat: Literal["CycloneDX"]
    specVersion: Literal["1.5", "1.6", "1.7"]
    version: int = Field(ge=1, strict=True)
    serialNumber: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list)
    externalReferences: list[dict[str, Any]] = Field(default_factory=list)
    vulnerabilities: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_FINDINGS)


class CycloneDxSource(BaseModel):
    name: str = ""
    url: str = ""


class CycloneDxRating(BaseModel):
    source: CycloneDxSource | None = None
    score: float | None = None
    severity: str = ""
    method: str = ""
    vector: str = ""


class CycloneDxFinding(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    source: CycloneDxSource | None = None
    description: str = ""
    detail: str = ""
    recommendation: str = ""
    ratings: list[CycloneDxRating] = Field(default_factory=list)
    cwes: list[int] = Field(default_factory=list)
    created: str = ""
    published: str = ""
    updated: str = ""
    analysis: dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=32768)
def valid_cpe(value: str) -> bool:
    try:
        if value.startswith("cpe:2.3:"):
            CPE2_3_FS(value)
        elif value.startswith("cpe:/"):
            CPE2_3_URI(value)
        else:
            return False
    except (ValueError, NotImplementedError):
        return False
    return True


def _component_inventory(component: CycloneDxComponent, reference: str) -> tuple[tuple, SbomComponent]:
    cpes = {p.value.strip() for p in component.properties if p.name == "syft:cpe23" and p.value.strip()}
    if component.cpe.strip():
        cpes.add(component.cpe.strip())
    purl = component.purl
    if purl:
        try:
            purl = PackageURL.from_string(purl).to_string()
        except ValueError:
            raise SbomValidationError("A component has an invalid package URL. Correct the SBOM and upload it again.") from None
    suppliers = sorted({s for s in (component.supplier.get("name"), component.publisher) if isinstance(s, str) and s})
    locations = sorted({p.value for p in component.properties if p.name.startswith("syft:location:") and p.name.endswith(":path")})
    item = SbomComponent(
        name=component.name,
        version=component.version,
        type=component.type,
        group=component.group,
        purl=purl,
        suppliers=suppliers,
        cpes=sorted(cpe for cpe in cpes if valid_cpe(cpe)),
        invalid_cpes=sorted(cpe for cpe in cpes if not valid_cpe(cpe)),
        occurrences=[SbomOccurrence(reference=reference, locations=locations)],
    )
    return component_identity(item.model_dump()), item


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


def parse_findings(records: list[dict], components: list[SbomComponent], declared_references: set[str]) -> list[SbomFinding]:
    references = {occurrence.reference for component in components for occurrence in component.occurrences} & declared_references
    findings: dict[tuple, SbomFinding] = {}
    reference_count = 0
    for record in records:
        try:
            CycloneDxFinding.model_validate(record)
        except ValidationError:
            raise SbomValidationError(
                "Each vulnerability must have an ID and correctly typed descriptions, sources, ratings, dates and analysis."
            ) from None
        identifier = record.get("id")
        source = record.get("source", {})
        affects = record.get("affects", [])
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or len(identifier) > 255
            or not isinstance(source, dict)
            or not isinstance(affects, list)
            or any(not isinstance(item, dict) or not isinstance(item.get("ref"), str) for item in affects)
        ):
            raise SbomValidationError("Each vulnerability must have an ID, a source object, and correctly typed component references.")
        reference_count += len(affects)
        if reference_count > MAX_FINDING_REFERENCES:
            raise SbomValidationError("The SBOM exceeds the limit of 1,000,000 vulnerability component references.")
        normalized = normalize_ioc_value(identifier, "cve")
        cve_id = normalized if re.fullmatch(r"CVE-\d{4}-\d{4,}", normalized) else ""
        key = (cve_id,) if cve_id else (identifier.strip(), json.dumps(source, sort_keys=True))
        finding = findings.setdefault(
            key, SbomFinding(identifier=cve_id or identifier.strip(), cve_id=cve_id, records=[], component_references=[])
        )
        finding.records.append(record)
        finding.component_references.extend(item["ref"] for item in affects)
    for finding in findings.values():
        supplied = set(finding.component_references)
        finding.component_references = sorted(supplied & references)
        finding.unresolved_references = sorted(supplied - references)
    return list(findings.values())


def parse_sbom(raw: bytes) -> ParsedSbom:
    try:
        document = CycloneDxDocument.model_validate(json.loads(raw))
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise SbomValidationError("Upload valid CycloneDX JSON version 1.5, 1.6, or 1.7 with a positive document version.") from None

    groups: dict[tuple, SbomComponent] = {}
    references: set[str] = set()
    software_records = excluded_files = total = 0
    pending = [(item, 0) for item in reversed(document.components)]
    root = document.metadata.get("component")
    if root is not None and not isinstance(root, dict):
        raise SbomValidationError("The SBOM metadata component must be an object.")
    if isinstance(root, dict):
        pending.append((root, 0))
    while pending:
        raw_component, depth = pending.pop()
        total += 1
        if total > MAX_COMPONENTS or depth > MAX_NESTING:
            raise SbomValidationError("The SBOM exceeds the limit of 100,000 component records or 64 nesting levels.")
        try:
            component = CycloneDxComponent.model_validate(raw_component)
            children = raw_component.get("components", [])
            if not isinstance(children, list) or any(not isinstance(child, dict) for child in children):
                raise ValueError
        except (ValidationError, ValueError, AttributeError):
            raise SbomValidationError("Each SBOM component must have a supported type, a name, and correctly typed metadata.") from None
        pending.extend((child, depth + 1) for child in reversed(children))
        if component.reference:
            if component.reference in references:
                raise SbomValidationError("The SBOM contains duplicate component references. Regenerate it with unique bom-ref values.")
            references.add(component.reference)
        if component.type == "file":
            # The metadata root is a scan target, not an inventory file.
            excluded_files += raw_component is not root
            continue
        software_records += 1
        identity, item = _component_inventory(component, component.reference)
        if existing := groups.get(identity):
            existing.occurrences.extend(item.occurrences)
            existing.cpes = sorted(set(existing.cpes) | set(item.cpes))
            existing.invalid_cpes = sorted(set(existing.invalid_cpes) | set(item.invalid_cpes))
            existing.suppliers = sorted(set(existing.suppliers) | set(item.suppliers))
        else:
            groups[identity] = item
    components = sorted(groups.values(), key=lambda c: (c.name.casefold(), c.version, c.purl, c.type))
    with_cpes = sum(bool(c.cpes) for c in components)
    if not with_cpes:
        raise SbomValidationError(
            "No valid CPEs were found on software components. Export an SBOM containing CPE 2.3 or CPE URI identifiers."
        )
    findings = parse_findings(document.vulnerabilities, components, references)
    affected_refs = {ref for finding in findings for ref in finding.component_references}
    try:
        subject_refs = root.get("externalReferences", []) if root else []
        document_refs = document.externalReferences
        # CycloneDX external references normally belong to the subject component.
        metadata_refs = document.metadata.get("externalReferences", [])
        if any(not isinstance(refs, list) for refs in (subject_refs, metadata_refs)):
            raise ValueError
        external_references = subject_refs + metadata_refs + document_refs
        for reference in external_references:
            CycloneDxSource.model_validate(reference)
        tools = document.metadata.get("tools", {})
        if not isinstance(tools, (dict, list)):
            raise TypeError
    except (ValidationError, ValueError, TypeError):
        raise SbomValidationError("The SBOM exporter tools and external references must contain correctly typed metadata.") from None
    source_name = str(root.get("name") or "") if root else ""
    name_parts = re.split(r"\s+/\s+", source_name.strip(), maxsplit=1)
    suggested_name = name_parts[1].strip() if len(name_parts) == 2 and all(part.strip() for part in name_parts) else source_name.strip()
    summary = SbomSummary(
        spec_version=document.specVersion,
        serial_number=document.serialNumber,
        document_version=document.version,
        generated_at=str(document.metadata.get("timestamp") or ""),
        suggested_name=suggested_name,
        source_name=source_name,
        software_records=software_records,
        excluded_files=excluded_files,
        component_count=len(components),
        components_with_cpes=with_cpes,
        invalid_cpe_count=sum(len(c.invalid_cpes) for c in components),
        description=str(root.get("description") or "") if root else "",
        tools=tools,
        external_references=external_references,
        vulnerabilities_supplied="vulnerabilities" in document.model_fields_set,
        finding_count=len(findings),
        cve_count=sum(bool(f.cve_id) for f in findings),
        affected_component_count=sum(any(o.reference in affected_refs for o in c.occurrences) for c in components),
        unresolved_reference_count=sum(len(f.unresolved_references) for f in findings),
    )
    return ParsedSbom(summary=summary, components=components, findings=findings)
