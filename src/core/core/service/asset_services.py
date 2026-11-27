"""Project observed services against the current inventory and its source-specific findings."""

from collections import defaultdict

from packageurl import PackageURL

from core.managers.db_manager import db
from core.model.asset import Asset
from core.model.asset_sbom import DiscoveryAsset, DiscoveryObservation
from core.model.user import User
from core.service.asset_sbom import SbomImportError, current_import


def host_provider(owner, packages):
    distro = owner["distribution"]
    if not (distro.get("id") and distro.get("version_id")):
        return None
    name = owner["name"].split(":")[0]
    matches = []
    for component in packages[name]:
        inventory = component.inventory
        if not inventory.get("purl") or inventory["version"] != owner["version"]:
            continue
        package = PackageURL.from_string(inventory["purl"])
        if (
            package.type == owner["ecosystem"]
            and package.name == name
            and package.version == owner["version"]
            and package.namespace == distro["id"]
            and package.qualifiers.get("arch") == owner["architecture"]
            and package.qualifiers.get("distro") in (distro["version_id"], distro["id"] + "-" + distro["version_id"])
        ):
            matches.append(component)
    return matches[0] if len(matches) == 1 else None


def image_provider(process, image, by_purl):
    executable = process.get("executable") or ""
    digest = process.get("executable_evidence") or {}
    if (
        not image
        or not executable.startswith("/")
        or executable.endswith(" (deleted)")
        or digest.get("status") != "complete"
        or not digest.get("sha256")
    ):
        return None
    identities = {
        (file["purl"], file["version"])
        for file in process.get("candidates", [])
        if file["file_path"] == executable and file["file_sha256"] == digest["sha256"] and file["image_id"] == image
    }
    if len(identities) != 1:
        return None
    matches = by_purl[next(iter(identities))]
    return matches[0] if len(matches) == 1 else None


def asset_services(asset_id: str, user: User):
    if Asset.get_for_api(asset_id, user.organization)[1] != 200:
        raise SbomImportError("Asset not found.", 404)
    bindings = db.session.scalars(db.select(DiscoveryAsset).filter_by(asset_id=asset_id, organization_id=user.organization.id)).all()
    snapshot = current_import(asset_id)
    packages = defaultdict(list)
    by_purl = defaultdict(list)
    if snapshot:
        for component in snapshot.components:
            packages[component.inventory["name"]].append(component)
            if component.inventory["purl"]:
                by_purl[component.inventory["purl"], component.inventory["version"]].append(component)
    services, running, history = [], [], []
    for binding in bindings:
        captures = db.session.scalars(
            db.select(DiscoveryObservation)
            .filter_by(asset_id=asset_id, source=binding.source)
            .order_by(DiscoveryObservation.observed_at.desc(), DiscoveryObservation.digest)
        ).all()
        parent = (
            db.session.get(DiscoveryAsset, (binding.organization_id, binding.source, binding.host)) if binding.host != binding.key else None
        )
        parent_id = parent.asset_id if parent and Asset.get_for_api(parent.asset_id, user.organization)[1] == 200 else None
        active, seen = True, set()
        for capture in captures:
            evidence = capture.evidence
            exact = snapshot and evidence.get("source_sha256") == snapshot.sha256
            image = snapshot and snapshot.summary.get("image_id") and snapshot.summary["image_id"] == evidence.get("image_id")
            basis = "exact snapshot" if exact else "image inventory" if image else None
            if not basis and snapshot and not evidence.get("source_sha256") and binding.link.get("sha256") == snapshot.sha256:
                basis = "asset binding"
            history.append(
                {
                    "source": binding.source,
                    "scope": binding.key,
                    "host": binding.host,
                    "parent_asset_id": parent_id,
                    "observed_at": capture.observed_at,
                    "digest": capture.digest,
                    "basis": basis,
                    "complete": evidence["complete"],
                }
            )
            for process in evidence["processes"]:
                running.append({"name": process["name"], "executable": process.get("executable"), "observed_at": capture.observed_at})
            if not active:
                continue
            for service in evidence["services"]:
                if service["key"] in seen:
                    continue
                seen.add(service["key"])
                candidates, providers, findings = {}, {}, []
                for process in service["processes"]:
                    for name in process["packages"]:
                        for component in packages[name]:
                            candidates[component.id] = component.inventory["name"]
                    if not basis:
                        continue
                    if binding.host == binding.key:
                        verified = [host_provider(owner, packages) for owner in process["package_details"]]
                    else:
                        verified = [image_provider(process, evidence["image_id"] if image else None, by_purl)]
                    providers.update({c.id: c for c in verified if c})
                references = {o["reference"] for c in providers.values() for o in c.inventory["occurrences"] if o["reference"]}
                if snapshot and references:
                    for finding in snapshot.findings:
                        records = [r for r in finding.details["records"] if any(a["ref"] in references for a in r.get("affects", []))]
                        if finding.cve_id and records:
                            findings.append({"cve": finding.cve_id, "records": records})
                services.append(
                    {
                        **service,
                        "scope": binding.key,
                        "observed_at": capture.observed_at,
                        "basis": basis,
                        "providers": {k: v.inventory["name"] for k, v in providers.items()},
                        "candidates": {k: v for k, v in candidates.items() if k not in providers},
                        "findings": findings,
                    }
                )
            active = not evidence["complete"]
    return {
        "asset_id": asset_id,
        "services": services,
        "processes": running,
        "captures": history,
        "snapshot": (
            {
                "sha256": snapshot.sha256,
                "generated_at": snapshot.summary["generated_at"],
                "components": snapshot.summary["component_count"],
                "assessed": snapshot.summary["vulnerabilities_supplied"],
            }
            if snapshot
            else None
        ),
    }
