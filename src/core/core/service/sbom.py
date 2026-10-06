"""Normalize CycloneDX software inventory without treating file records as packages."""

import json
from functools import lru_cache
from typing import Any, Literal

from cpe.cpe2_3_fs import CPE2_3_FS
from cpe.cpe2_3_uri import CPE2_3_URI
from models.sbom import SbomComponent, SbomOccurrence, SbomSummary
from packageurl import PackageURL
from pydantic import BaseModel, Field, ValidationError


MAX_COMPONENTS = 100_000
MAX_NESTING = 64


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
        purl=purl,
        suppliers=suppliers,
        cpes=sorted(cpe for cpe in cpes if valid_cpe(cpe)),
        invalid_cpes=sorted(cpe for cpe in cpes if not valid_cpe(cpe)),
        occurrences=[SbomOccurrence(reference=reference, locations=locations)],
    )
    # Without a package URL, only group records whose supplier and CPE identity also agree.
    identity = (
        (component.type, purl, component.version)
        if purl
        else (
            component.type,
            component.group,
            component.name,
            component.version,
            tuple(suppliers),
            tuple(item.cpes),
            tuple(item.invalid_cpes),
        )
    )
    return identity, item


def parse_sbom(raw: bytes) -> tuple[SbomSummary, list[SbomComponent]]:
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
        identity, item = _component_inventory(component, component.reference or f"record:{total}")
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
    summary = SbomSummary(
        spec_version=document.specVersion,
        serial_number=document.serialNumber,
        document_version=document.version,
        generated_at=str(document.metadata.get("timestamp") or ""),
        suggested_name=str(root.get("name") or "") if root else "",
        software_records=software_records,
        excluded_files=excluded_files,
        component_count=len(components),
        components_with_cpes=with_cpes,
        invalid_cpe_count=sum(len(c.invalid_cpes) for c in components),
    )
    return summary, components
