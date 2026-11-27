"""Resolve collector scope within an organization and apply prepared inventory atomically."""

from datetime import datetime
from hashlib import sha256

from models.discovery import PreparedDiscovery, Scope
from sqlalchemy import or_, select

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_sbom import (
    AssetSbomImport,
    AssetSbomUpload,
    DiscoveryAsset,
    DiscoveryDestination,
    DiscoveryImport,
    DiscoveryObservation,
)
from core.model.organization import Organization
from core.model.user import User
from core.service.asset_sbom import SbomImportError, apply_snapshot, current_import
from core.service.sbom_upload import queue_upload


def stage_discovery(files: list[tuple[str, bytes]], source: str, user: User):
    if queue_manager.queue_manager.queue_action_error():
        raise SbomImportError("Discovery processing is unavailable. Please try again later.", 503)
    filename, raw = files[0]
    upload = AssetSbomUpload(
        user_id=user.id,
        organization_id=user.organization.id,
        target_asset_id=None,
        filename=filename,
        source=raw,
        sha256=sha256(raw).hexdigest(),
    )
    db.session.add(upload)
    db.session.flush()
    discovery = DiscoveryImport()
    discovery.upload_id, discovery.source = upload.id, source
    if len(files) == 2:
        discovery.second_name, discovery.second_file = files[1]
        discovery.second_hash = sha256(files[1][1]).hexdigest()
    db.session.add(discovery)
    return queue_upload(upload)


def prepare(upload: AssetSbomUpload, job: DiscoveryImport, data: PreparedDiscovery):
    if job.prepared is not None:
        return
    evidence_digest = upload.sha256 if data.sbom_file != 1 else job.second_hash
    if data.sbom_file == 2:
        if not job.second_hash or not job.second_name:
            raise SbomImportError("Second input unavailable.", 409)
        upload.sha256, upload.filename = job.second_hash, job.second_name
    job.prepared = {**data.model_dump(mode="json"), "evidence_digest": evidence_digest}


def destination(job, user, choice):
    org = user.organization
    saved = db.session.get(DiscoveryDestination, (org.id, job.source))
    groups = db.session.scalars(db.select(AssetGroup).where(or_(AssetGroup.organization_id == org.id, AssetGroup.key == "default"))).all()
    options = {g.id: g for g in groups}
    if choice and choice not in options:
        raise SbomImportError("Destination group unavailable.", 403)
    group_id = choice or (saved.group_id if saved else None) or (groups[0].id if len(groups) == 1 else None)
    if group_id not in options:
        job.result = {
            "state": "review",
            "reason": "destination",
            "message": "Choose the destination group for this inventory source.",
            "groups": [{"id": g.id, "name": g.name} for g in groups],
        }
        return None
    if choice:
        if not saved:
            saved = DiscoveryDestination()
            saved.organization_id, saved.source = org.id, job.source
            db.session.add(saved)
        saved.group_id = choice
    return options[group_id]


def discover_scopes(job, user, group, scopes, digest, choice):
    for scope in scopes:
        binding = db.session.get(DiscoveryAsset, (user.organization.id, job.source, scope.key))
        if binding:
            if Asset.get_for_api(binding.asset_id, user.organization)[1] != 200:
                raise SbomImportError("The destination asset is unavailable.", 403)
        else:
            assert group is not None
            matches = db.session.scalars(
                db.select(Asset)
                .filter_by(name=scope.key, asset_group_id=group.id)
                .where(~db.select(DiscoveryAsset.asset_id).where(DiscoveryAsset.asset_id == Asset.id).exists())
            ).all()
            selection = choice.get("asset_id") if job.result.get("reason") == "identity" and job.result.get("scope") == scope.key else None
            if matches and selection not in ["new", *(a.id for a in matches)]:
                job.result = {
                    "state": "review",
                    "reason": "identity",
                    "scope": scope.key,
                    "message": "An existing asset has this name. Choose whether it represents this collector scope.",
                    "options": [{"id": a.id, "name": a.name} for a in matches],
                }
                return False
            asset = next((a for a in matches if a.id == selection), None)
            if not asset:
                asset = Asset(name=scope.key, serial="", description="", group=group, tags=[])
                db.session.add(asset)
                db.session.flush()
            binding = DiscoveryAsset()
            binding.organization_id, binding.source, binding.key = user.organization.id, job.source, scope.key
            binding.asset_id, binding.host = asset.id, scope.host
            db.session.add(binding)
        if not db.session.get(DiscoveryObservation, (binding.asset_id, job.source, digest)):
            observation = DiscoveryObservation()
            observation.asset_id, observation.source, observation.digest = binding.asset_id, job.source, digest
            observation.observed_at = scope.observed_at.isoformat(timespec="microseconds")
            observation.evidence = scope.model_dump(mode="json")
            db.session.add(observation)
    return True


def apply_discovery(upload: AssetSbomUpload, job: DiscoveryImport, user: User, choice: dict):
    if job.result.get("state") == "applied":
        return None
    # Serialize source bindings and destination creation, including on SQLite.
    db.session.execute(db.update(Organization).where(Organization.id == user.organization.id).values(name=Organization.name))
    data = job.prepared or {}
    scopes = [Scope.model_validate(s) for s in data["scopes"]]
    record = db.session.get(AssetSbomImport, upload.import_id) if upload.import_id else None
    exact = scopes[0].source_sha256 if len(scopes) == 1 else None
    if (
        record
        and exact
        and (
            record.sha256 != exact
            or (record.summary.get("image_id") and scopes[0].key == scopes[0].host)
            or (record.summary.get("image_id") and scopes[0].image_id and record.summary["image_id"] != scopes[0].image_id)
        )
    ):
        job.result = {
            "state": "review",
            "reason": "mismatch",
            "expected_sha256": exact,
            "uploaded_sha256": record.sha256,
            "scope": scopes[0].key,
            "message": "The service sidecar and SBOM identities disagree. Upload the matching files.",
        }
        return None
    needs_group = any(not db.session.get(DiscoveryAsset, (user.organization.id, job.source, s.key)) for s in scopes)
    group = destination(job, user, choice.get("group_id")) if needs_group else None
    if needs_group and not group:
        return None
    if not discover_scopes(job, user, group, scopes, data.get("evidence_digest"), choice):
        return None
    db.session.flush()
    bindings = db.session.scalars(db.select(DiscoveryAsset).filter_by(organization_id=user.organization.id, source=job.source)).all()
    observed_keys = {s.key for s in scopes}
    observed = [b for b in bindings if b.key in observed_keys]
    result = {"state": "applied", "assets": [{"id": b.asset_id, "name": b.key} for b in observed]}
    # A separately arriving sidecar may complete an earlier private inventory upload.
    pending = None
    if not record and scopes:
        waiting = db.session.execute(
            select(DiscoveryImport, AssetSbomImport)
            .join(AssetSbomUpload, AssetSbomUpload.id == DiscoveryImport.upload_id)
            .join(AssetSbomImport, AssetSbomImport.id == AssetSbomUpload.import_id)
            .where(
                DiscoveryImport.source == job.source,
                AssetSbomUpload.user_id == user.id,
                AssetSbomUpload.organization_id == user.organization.id,
                AssetSbomImport.asset_id.is_(None),
            )
            .order_by(AssetSbomUpload.created.desc())
        ).all()
        for other, snapshot in waiting:
            if (
                other.result.get("reason") == "scope"
                and not (other.prepared or {}).get("scopes")
                and (
                    exact == snapshot.sha256
                    or not exact
                    and any(s.image_id and s.image_id == snapshot.summary.get("image_id") for s in scopes)
                )
            ):
                pending, record = other, snapshot
                break
    if not record:
        job.result = result
        return None
    image = record.summary.get("image_id")
    allowed = observed if scopes else list(bindings)
    candidates = []
    basis = "exact snapshot"
    for binding in allowed:
        if Asset.get_for_api(binding.asset_id, user.organization)[1] != 200:
            continue
        captures = db.session.scalars(
            db.select(DiscoveryObservation)
            .filter_by(asset_id=binding.asset_id, source=job.source)
            .order_by(DiscoveryObservation.observed_at.desc())
        ).all()
        relevant = [c for c in captures if not scopes or c.digest == data.get("evidence_digest")]
        if any(c.evidence.get("source_sha256") == record.sha256 for c in relevant):
            candidates.append((binding, "exact snapshot"))
        elif image and relevant and relevant[0].evidence.get("image_id") == image and not relevant[0].evidence.get("source_sha256"):
            candidates.append((binding, "image inventory"))
    if len(candidates) != 1:
        remembered = [
            (b, "analyst selection")
            for b in allowed
            if b.link.get("basis") == "analyst selection"
            and b.link.get("sha256") == record.sha256
            and Asset.get_for_api(b.asset_id, user.organization)[1] == 200
        ]
        if len(remembered) == 1:
            candidates = remembered
    if job.result.get("reason") == "replacement" and choice.get("expected_sha256"):
        candidates = [
            (b, job.result["basis"])
            for b in allowed
            if b.key == job.result["scope"] and Asset.get_for_api(b.asset_id, user.organization)[1] == 200
        ]
    selected = choice.get("scope")
    if selected:
        if job.result.get("reason") != "scope" or selected not in [o["key"] for o in job.result.get("options", [])]:
            raise SbomImportError("The selected scope is unavailable.", 409)
        candidates = [
            (b, "analyst selection") for b in allowed if b.key == selected and Asset.get_for_api(b.asset_id, user.organization)[1] == 200
        ]
    if len(candidates) != 1:
        options = [b for b, _ in candidates] or allowed
        job.result = {
            **result,
            "state": "review",
            "reason": "scope",
            "message": "Choose the scope for this inventory or import matching discovery.",
            "options": [{"key": b.key} for b in options if Asset.get_for_api(b.asset_id, user.organization)[1] == 200],
        }
        return None
    binding, basis = candidates[0]
    asset = db.session.get(Asset, binding.asset_id, with_for_update=True)
    previous = current_import(binding.asset_id)
    changed = False
    if choice.get("expected_sha256") and (not previous or previous.sha256 != choice["expected_sha256"]):
        job.result = {
            **result,
            "state": "review",
            "reason": "replacement",
            "scope": binding.key,
            "basis": basis,
            "expected_sha256": previous.sha256 if previous else "",
            "message": "The asset inventory changed since review. Confirm the current replacement.",
        }
        return None
    if previous and previous.sha256 == record.sha256:
        if previous.id != record.id:
            db.session.delete(record)
            upload.import_id = previous.id
    else:
        if previous:
            before, after = previous.summary.get("generated_at"), record.summary.get("generated_at")
            try:
                older = bool(before and after and datetime.fromisoformat(after) < datetime.fromisoformat(before))
            except (ValueError, TypeError):
                older = True
            if (older or previous.findings and not record.summary.get("vulnerabilities_supplied")) and (
                job.result.get("reason") != "replacement" or choice.get("expected_sha256") != previous.sha256
            ):
                job.result = {
                    **result,
                    "state": "review",
                    "reason": "replacement",
                    "basis": basis,
                    "scope": binding.key,
                    "expected_sha256": previous.sha256,
                    "message": "This inventory is older or would clear reported findings. Confirm replacement.",
                }
                return None
        asset, changed = apply_snapshot(
            record.id,
            user,
            create=None,
            asset_id=binding.asset_id,
            expected_sha256=previous.sha256 if previous else None,
            enable_cve_matching=True,
            discovery=True,
            enable_software_matching=True,
        )
    if not (binding.link.get("sha256") == record.sha256 and binding.link.get("basis") == "exact snapshot"):
        binding.link = {"sha256": record.sha256, "basis": basis, "image_id": image}
    if not observed:
        result["assets"] = [{"id": binding.asset_id, "name": binding.key}]
    result["inventory_asset_id"] = binding.asset_id
    job.result = result
    if pending:
        pending.result = result
    return asset if changed else None
