"""Stage private uploads and persist worker-prepared inventory in bounded batches."""

import hashlib
from datetime import timedelta

from models.sbom import SBOM_PARSER_VERSION, SbomComponentBatch, SbomFindingBatch, SbomSummary, SbomUploadStatus
from sqlalchemy import select

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFinding, AssetSbomImport, AssetSbomUpload, AssetSbomUploadReference
from core.model.task import Task
from core.model.user import User
from core.service.asset_sbom import SbomImportError


PREPARATION_FAILED = "Unable to prepare the SBOM. Upload the file again to retry."
TERMINAL_STATUSES = {"READY", "FAILED"}


def upload_status(upload: AssetSbomUpload) -> dict:
    return SbomUploadStatus.model_validate(upload, from_attributes=True).model_dump()


def accessible_upload(upload_id: str, user: User | None = None) -> AssetSbomUpload:
    upload = db.session.scalar(db.select(AssetSbomUpload).filter_by(id=upload_id).with_for_update())
    if not upload or (user and (upload.user_id != user.id or upload.organization_id != user.organization.id)):
        raise SbomImportError("SBOM upload unavailable.", 404)
    if upload.status == "READY" and not upload.import_id:
        raise SbomImportError("SBOM preview no longer available.", 404)
    owner = user or (db.session.get(User, upload.user_id) if upload.user_id else None)
    authorized = owner and owner.organization.id == upload.organization_id and "ASSETS_CREATE" in owner.get_permissions()
    if not owner or not authorized or (upload.target_asset_id and Asset.get_for_api(upload.target_asset_id, owner.organization)[1] != 200):
        fail_upload(upload, "Access to this SBOM upload is no longer available.")
        raise SbomImportError("SBOM upload unavailable.", 404)
    return upload


def fail_upload(upload: AssetSbomUpload, message: str = PREPARATION_FAILED) -> None:
    if upload.status in TERMINAL_STATUSES:
        return
    upload.status, upload.error, upload.source = "FAILED", message, None
    db.session.execute(db.delete(AssetSbomUploadReference).filter_by(upload_id=upload.id))
    if record := db.session.get(AssetSbomImport, upload.import_id) if upload.import_id else None:
        upload.import_id = None
        db.session.delete(record)
    db.session.commit()


def refresh_upload(upload: AssetSbomUpload) -> None:
    if upload.status in TERMINAL_STATUSES:
        return
    task = Task.get_by_job_id(upload.id)
    expired = upload.utcnow() - upload.updated > timedelta(hours=24 if upload.status == "QUEUED" else 1)
    if expired or (task and task.status == "FAILURE"):
        fail_upload(upload)


def stage_upload(raw: bytes, filename: str, user: User, target_asset_id: str | None) -> AssetSbomUpload:
    manager = queue_manager.queue_manager
    if manager.queue_action_error():
        raise SbomImportError("SBOM processing is unavailable. Please try again later.", 503)
    if target_asset_id and Asset.get_for_api(target_asset_id, user.organization)[1] != 200:
        raise SbomImportError("Asset not found.", 404)
    digest = hashlib.sha256(raw).hexdigest()
    previous = db.session.scalars(
        db.select(AssetSbomImport)
        .filter_by(sha256=digest, user_id=user.id, organization_id=user.organization.id)
        .where(
            ~db.select(AssetSbomUpload.id).where(AssetSbomUpload.import_id == AssetSbomImport.id, AssetSbomUpload.status != "READY").exists()
        )
        .order_by(AssetSbomImport.created.desc())
    )
    for record in previous:
        if target_asset_id and record.asset_id not in (None, target_asset_id):
            continue
        if record.summary.get("parser_version") == SBOM_PARSER_VERSION and (
            not record.asset_id or Asset.get_for_api(record.asset_id, user.organization)[1] == 200
        ):
            upload = AssetSbomUpload(
                user_id=user.id,
                organization_id=user.organization.id,
                target_asset_id=target_asset_id,
                filename=filename,
                sha256=digest,
                status="READY",
                import_id=record.id,
            )
            db.session.add(upload)
            db.session.commit()
            return upload
    upload = db.session.scalar(
        db.select(AssetSbomUpload)
        .filter_by(user_id=user.id, organization_id=user.organization.id, target_asset_id=target_asset_id, sha256=digest)
        .where(AssetSbomUpload.status.in_(("QUEUED", "PROCESSING")))
    )
    if upload:
        refresh_upload(upload)
        if upload.status != "FAILED":
            return upload
    upload = AssetSbomUpload(
        user_id=user.id, organization_id=user.organization.id, target_asset_id=target_asset_id, filename=filename, sha256=digest, source=raw
    )
    db.session.add(upload)
    db.session.commit()
    if not manager.enqueue_task(
        "misc",
        "sbom_import_task",
        upload.id,
        job_id=upload.id,
        job_timeout=1800,
        meta={"task": "sbom_import_task", "user_id": user.id, "worker_id": upload.id, "worker_type": "sbom_import_task"},
    ):
        fail_upload(upload, "Unable to queue SBOM processing. Upload the file again to retry.")
        raise SbomImportError(upload.error, 503)
    return upload


def begin_preview(upload: AssetSbomUpload, summary: SbomSummary) -> None:
    if upload.status in TERMINAL_STATUSES or upload.import_id:
        return
    if summary.component_count < 1 or summary.finding_count < 0 or summary.parser_version != SBOM_PARSER_VERSION:
        raise SbomImportError("Invalid prepared SBOM summary.", 400)
    assert upload.user_id is not None
    record = AssetSbomImport(upload.filename, upload.sha256, upload.user_id, upload.organization_id, summary.model_dump())
    db.session.add(record)
    db.session.flush()
    upload.import_id = record.id
    upload.status = "PROCESSING"


def reference_hash(reference: str) -> str:
    """Keep database index keys bounded even when an exporter uses long component references."""
    return hashlib.sha256(reference.encode()).hexdigest()


def persist_batch(upload: AssetSbomUpload, batch: SbomComponentBatch | SbomFindingBatch) -> None:
    record = db.session.get(AssetSbomImport, upload.import_id) if upload.import_id else None
    if upload.status != "PROCESSING" or not record:
        raise SbomImportError("This SBOM is not accepting prepared inventory.", 409)
    components = isinstance(batch, SbomComponentBatch)
    received = upload.components_received if components else upload.findings_received
    expected = record.summary["component_count" if components else "finding_count"]
    if batch.offset + len(batch.items) <= received:
        return
    if batch.offset != received or received + len(batch.items) > expected:
        raise SbomImportError("SBOM batches must arrive in order.", 409)
    if isinstance(batch, SbomComponentBatch):
        rows = [
            {"id": AssetSbomComponent.uuid7_str(), "import_id": record.id, "position": position, "inventory": item.model_dump()}
            for position, item in enumerate(batch.items, start=received)
        ]
        db.session.execute(db.insert(AssetSbomComponent), rows)
        references = [
            {"upload_id": upload.id, "reference_hash": reference_hash(occurrence.reference), "component_id": row["id"]}
            for row, item in zip(rows, batch.items, strict=True)
            for occurrence in item.occurrences
            if occurrence.reference
        ]
        if references:
            db.session.execute(db.insert(AssetSbomUploadReference), references)
        upload.components_received += len(batch.items)
        return
    if upload.components_received != record.summary["component_count"]:
        raise SbomImportError("Prepare all components before findings.", 409)
    references = {ref for item in batch.items for ref in item.component_references}
    by_reference = dict(
        db.session.execute(
            select(AssetSbomUploadReference.reference_hash, AssetSbomUploadReference.component_id).where(
                AssetSbomUploadReference.upload_id == upload.id,
                AssetSbomUploadReference.reference_hash.in_([reference_hash(ref) for ref in references]),
            )
        ).all()
    )
    if {reference_hash(ref) for ref in references} - by_reference.keys():
        raise SbomImportError("Prepared findings reference unknown components.", 400)
    components_by_id = {
        c.id: c for c in db.session.scalars(db.select(AssetSbomComponent).where(AssetSbomComponent.id.in_(set(by_reference.values()))))
    }
    for item in batch.items:
        finding = AssetSbomFinding()
        finding.import_id = record.id
        finding.identifier, finding.cve_id = item.identifier, item.cve_id
        finding.matching_enabled = bool(item.cve_id)
        finding.details = item.model_dump(exclude={"identifier", "cve_id", "component_references"})
        finding.components = [
            components_by_id[cid] for cid in dict.fromkeys(by_reference[reference_hash(ref)] for ref in item.component_references)
        ]
        db.session.add(finding)
    upload.findings_received += len(batch.items)


def finish_preview(upload: AssetSbomUpload) -> None:
    if upload.status == "READY":
        return
    record = db.session.get(AssetSbomImport, upload.import_id) if upload.import_id else None
    if (
        not record
        or upload.status != "PROCESSING"
        or (upload.components_received != record.summary["component_count"] or upload.findings_received != record.summary["finding_count"])
    ):
        raise SbomImportError("The prepared SBOM is incomplete.", 409)
    upload.status, upload.source = "READY", None
    db.session.execute(db.delete(AssetSbomUploadReference).filter_by(upload_id=upload.id))


def expire_uploads() -> None:
    """Release abandoned source files even when the user never returns to the progress page."""
    now = AssetSbomUpload.utcnow()
    stale_ids = db.session.scalars(
        db.select(AssetSbomUpload.id).where(
            ((AssetSbomUpload.status == "QUEUED") & (AssetSbomUpload.updated < now - timedelta(hours=24)))
            | ((AssetSbomUpload.status == "PROCESSING") & (AssetSbomUpload.updated < now - timedelta(hours=1)))
        )
    ).all()
    for upload_id in stale_ids:
        upload = db.session.scalar(db.select(AssetSbomUpload).filter_by(id=upload_id).with_for_update())
        if upload:
            refresh_upload(upload)
