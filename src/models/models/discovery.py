"""Normalize saved ScanMate reports and SBOMProber service inventories for asset imports."""

import json
import re
from datetime import UTC
from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import AwareDatetime, BaseModel, Field, StrictBool, field_validator, model_validator

from models.sbom_parser import SbomValidationError


Name = Annotated[str, Field(min_length=1, max_length=255)]
Segment = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Image = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
Port = Annotated[int, Field(strict=True, ge=1, le=65535)]
INVALID = "Invalid discovery data. Check the scope, timestamps, endpoint fields and source references."


class PackageOwner(BaseModel):
    name: Name
    version: Name
    architecture: Name
    ecosystem: Literal["deb", "rpm"]
    distribution: dict[str, str] = Field(default_factory=dict, max_length=2)


class ExecutableEvidence(BaseModel):
    status: Literal["complete", "unavailable", "changed", "size_limit", "read_limit"]
    sha256: Digest | None = None


class PackageFile(BaseModel):
    """A retained Syft relationship in the collector output, scoped to its scanned image."""

    image_id: Image
    native_id: Name
    relationship: Literal["contains", "binary-evidence"]
    file_path: str = Field(min_length=1, max_length=4096)
    file_sha256: Digest
    purl: str = Field(min_length=1, max_length=2048)
    version: Name


class Process(BaseModel):
    name: Name
    executable: str | None = Field(default=None, max_length=4096)
    executable_evidence: ExecutableEvidence | None = None
    candidates: list[PackageFile] = Field(default_factory=list, max_length=100)
    packages: list[Name] = Field(default_factory=list, max_length=100)
    package_details: list[PackageOwner] = Field(default_factory=list, max_length=100)


class Endpoint(BaseModel):
    kind: Literal["listener", "declared", "published", "probed", "peer"]
    protocol: Literal["tcp", "udp"]
    address: str | None = None
    port: Port
    container_port: Port | None = None
    namespace: str | None = Field(default=None, max_length=255)

    @field_validator("address")
    @classmethod
    def numeric_address(cls, value):
        return str(ip_address(value)) if value else None


class Service(BaseModel):
    key: Name
    name: Name
    version: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=16000)
    endpoints: list[Endpoint] = Field(max_length=1000)
    processes: list[Process] = Field(default_factory=list, max_length=1000)


class Scope(BaseModel):
    key: Name
    host: Segment
    image_id: Image | None = None
    source_sha256: Digest | None = None
    observed_at: AwareDatetime
    complete: StrictBool
    services: list[Service] = Field(default_factory=list, max_length=10000)
    processes: list[Process] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def scoped_identity(self):
        if self.key != self.host:
            parts = self.key.split("/")
            if (
                parts[:2] != [self.host, "docker"]
                or (len(parts) != 6 or parts[2] != "compose")
                and (len(parts) != 4 or parts[2] != "container")
                or any(part in (".", "..") or not re.fullmatch(r"(?:[A-Za-z0-9_.~-]|%[0-9A-F]{2})+", part) for part in parts[3:])
            ):
                raise ValueError("Invalid workload identity")
        if len({s.key for s in self.services}) != len(self.services):
            raise ValueError("Duplicate service")
        self.observed_at = self.observed_at.astimezone(UTC)
        return self


class PreparedDiscovery(BaseModel):
    sbom_file: Literal[1, 2] | None = None
    scopes: list[Scope] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique_scopes(self):
        if len({scope.key for scope in self.scopes}) != len(self.scopes) or not (self.scopes or self.sbom_file):
            raise ValueError("Missing or duplicate scope")
        return self


def distinct_processes(processes):
    unique = {}
    for raw in processes:
        process = Process.model_validate(raw)
        unique[process.model_dump_json()] = process
    return list(unique.values())


def sidecar(document):
    host, key = document["inventory_hostname"], document["asset_name"]
    if not document["source_sha256"] or document["asset_type"] != ("host" if key == host else "container"):
        raise ValueError
    scope = Scope(
        host=host,
        key=key,
        image_id=document.get("image_id"),
        source_sha256=document["source_sha256"],
        observed_at=document["observed_at"],
        complete=document["complete"],
    )
    services = []
    if not isinstance(document["services"], list) or len(document["services"]) > 10000:
        raise ValueError
    for raw in document["services"]:
        properties = {p["name"]: p["value"] for p in raw["properties"]}
        endpoints, processes = [], []
        for item in json.loads(properties["sbomprober:services:evidence"]):
            kind = item["kind"]
            if kind not in {"declared", "published", "listener"}:
                raise ValueError
            endpoints.append(
                Endpoint(
                    kind=kind,
                    protocol=item["protocol"],
                    address=item.get("address", item.get("host_address")),
                    port=item.get("port", item.get("host_port", item.get("container_port"))),
                    container_port=item.get("container_port"),
                    namespace=item.get("network_namespace"),
                )
            )
            for process in item.get("processes", []):
                if process.get("container_id") == document.get("container_id") and (key == host or document.get("container_id")):
                    processes.append(process)
        services.append(
            Service(
                key=raw["bom-ref"],
                name=raw["name"],
                description=raw.get("description", ""),
                version=raw.get("version", ""),
                endpoints=endpoints,
                processes=distinct_processes(processes),
            )
        )
    return [scope.model_copy(update={"services": services})]


def report(document):
    when = document["collected_at"]
    for key, limit in (("hosts", 1000), ("containers", 1000), ("network_namespaces", 10000), ("processes", 10000), ("endpoints", 10000)):
        if not isinstance(document[key], list) or len(document[key]) > limit:
            raise ValueError
    if not document["hosts"] or document["status"] not in ("complete", "partial", "failed"):
        raise ValueError
    hosts, workloads, namespaces, processes = {}, {}, {}, {}
    for item in document["hosts"]:
        complete = document["status"] == "complete" and all(
            v == "complete" for k, v in item["collection"].items() if k in ("runtime", "docker", "external")
        )
        hosts[item["id"]] = Scope(key=item["alias"], host=item["alias"], observed_at=when, complete=complete)
    for item in document["containers"]:
        host = hosts[item["host_id"]]
        identity = item["identity"]
        if not isinstance(identity, list) or not identity:
            raise ValueError
        key = "/".join(
            [
                host.key,
                "docker",
                "container" if identity[0] == "name" else identity[0],
                *(quote(str(segment), safe="") for segment in identity[1:]),
            ]
        )
        workloads[item["id"]] = Scope(key=key, host=host.key, image_id=item.get("image_id"), observed_at=when, complete=host.complete)
    for item in document["network_namespaces"]:
        host = hosts[item["host_id"]]
        owners = [workloads[k] for k in item["container_ids"]]
        if any(s.host != host.key for s in owners):
            raise ValueError
        namespaces[item["id"]] = (host, owners, item["is_host"])
    for item in document["processes"]:
        host = hosts[item["host_id"]]
        owner = workloads[item["container_id"]] if item.get("container_id") else host
        if owner.host != host.key:
            raise ValueError
        process = Process.model_validate(item)
        processes[item["id"]] = owner, process
        owner.processes.append(process)
    # Shared process references must stay bounded when expanded into endpoint evidence.
    process_sizes = {k: len(p.model_dump_json().encode()) for k, (_, p) in processes.items()}
    expanded_size = 0
    for item in document["endpoints"]:
        expanded_size += sum(process_sizes[k] for k in item["process_ids"])
        if len(item["process_ids"]) > 1000 or expanded_size > 32 * 1024 * 1024:
            raise ValueError
        if not item.get("host_id"):
            continue
        host = hosts[item["host_id"]]
        ns = item.get("network_namespace_id")
        owners = [workloads[k] for k in item["container_ids"]]
        if ns:
            ns_host, ns_owners, is_host = namespaces[ns]
            if ns_host != host or any(s.host != host.key or (not is_host and s not in ns_owners) for s in owners):
                raise ValueError
            owners = owners or ([host] if is_host else ns_owners)
        if any(s.host != host.key for s in owners):
            raise ValueError
        endpoint_processes = [processes[k] for k in item["process_ids"]]
        if any(scope.host != host.key for scope, _ in endpoint_processes):
            raise ValueError
        if len(owners) > 1:
            owners = [s for s in owners if any(p_scope is s for p_scope, _ in endpoint_processes)]
            if not owners:
                continue
        if "runtime_observed" in item and type(item["runtime_observed"]) is not bool:
            raise ValueError
        discovery = item.get("discovery", {})
        kind = "listener" if item.get("runtime_observed") else "probed" if discovery else "peer"
        endpoint = Endpoint(kind=kind, address=item["address"], port=item["port"], protocol=item["protocol"], namespace=ns)
        detected = discovery.get("product") if discovery.get("method") == "probed" else None
        for owner in owners or [host]:
            owner.services.append(
                Service(
                    key=item["id"],
                    name=detected or f"{endpoint.protocol}/{endpoint.port}",
                    version=discovery.get("version", "") if detected else "",
                    endpoints=[endpoint],
                    processes=[process for scope, process in endpoint_processes if scope is owner],
                )
            )
    if any(
        len(lookup) != len(document[key])
        for lookup, key in ((hosts, "hosts"), (workloads, "containers"), (namespaces, "network_namespaces"), (processes, "processes"))
    ):
        raise ValueError
    return [*hosts.values(), *workloads.values()]


def prepare_discovery(files: list[bytes]) -> PreparedDiscovery:
    sbom_file = None
    scopes = None
    try:
        for index, raw in enumerate(files, 1):
            document = json.loads(raw)
            if document.get("bomFormat") == "CycloneDX" and sbom_file is None:
                sbom_file = index
            elif scopes is None and type(document.get("schema_version")) is int and document["schema_version"] in (1, 2):
                scopes = sidecar(document) if document["schema_version"] == 1 else report(document)
            else:
                raise ValueError
        # Revalidate the assembled lists after projecting collector-specific fields.
        return PreparedDiscovery.model_validate({"sbom_file": sbom_file, "scopes": [s.model_dump() for s in scopes or []]})
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, IndexError):
        raise SbomValidationError(INVALID) from None
