"""User-scoped SBOM previews, replacement, and imported CVE matching decisions."""

import re
from math import ceil

from flask import Response, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.cti import normalize_ioc_value
from models.discovery import PreparedDiscovery
from models.sbom import SbomComponentBatch, SbomCreateAsset, SbomCveMatching, SbomFindingBatch, SbomInventory, SbomReplaceAsset, SbomSummary
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from core.managers.auth_manager import api_key_required, auth_required
from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetTrigger
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFinding, AssetSbomImport, DiscoveryImport
from core.model.user import User
from core.service.asset_discovery import apply_discovery, prepare_discovery_import, stage_discovery
from core.service.asset_intelligence import asset_triggers, start_match_run, trigger_suggestions
from core.service.asset_sbom import SbomImportError, apply_import, compare_import, current_import, owned_import
from core.service.asset_services import asset_services
from core.service.cache_invalidation import invalidate_frontend_cache_on_success
from core.service.sbom_upload import (
    accessible_upload,
    begin_preview,
    fail_upload,
    finish_preview,
    persist_batch,
    refresh_upload,
    stage_upload,
    upload_status,
)


PAGE_SIZE = 50


def inventory_response(record: AssetSbomImport) -> dict:
    pages = max(1, ceil(record.summary["component_count"] / PAGE_SIZE))
    page = min(pages, max(1, request.args.get("page", default=1, type=int)))
    components = db.session.scalars(
        db.select(AssetSbomComponent)
        .filter_by(import_id=record.id)
        .order_by(AssetSbomComponent.position)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    comparison = None
    if target_id := request.args.get("asset_id"):
        if Asset.get_for_api(target_id, current_user.organization)[1] != 200:
            raise SbomImportError("Asset not found.", 404)
        target = Asset.get(target_id)
        assert target is not None
        comparison = compare_import(record, target)
    return SbomInventory(
        id=record.id,
        asset_id=record.asset_id,
        filename=record.filename,
        sha256=record.sha256,
        imported_at=record.serialize_datetime(record.confirmed or record.created),
        summary=record.summary,
        components=[{**c.inventory, "id": c.id, "suggestions": trigger_suggestions(c.inventory)} for c in components],
        page=page,
        pages=pages,
        comparison=comparison,
    ).model_dump(mode="json")


def applied_response(asset: Asset, changed: bool, status: int, user=None):
    user = user or current_user
    if changed:
        invalidate_frontend_cache_on_success(status, models=("asset",), object_ids={"asset": asset.id})
        if {"ASSETS_ACCESS", "ASSESS_ACCESS"}.issubset(user.get_permissions()) and db.session.scalar(
            asset_triggers(asset.id).where(AssetTrigger.enabled.is_(True)).limit(1)
        ):
            start_match_run(asset.id, user)
    return {"id": asset.id, "message": "SBOM applied." if changed else "This SBOM has already been applied."}, status if changed else 200


class SbomUpload(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self):
        upload = request.files.get("file")
        if not upload:
            return {"error": "Select a CycloneDX JSON file."}, 400
        try:
            upload_job = stage_upload(
                upload.read(),
                secure_filename(upload.filename or "sbom.json")[:255] or "sbom.json",
                current_user,
                target_asset_id=request.args.get("asset_id") or None,
            )
            return upload_status(upload_job), 200 if upload_job.status == "READY" else 202
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


class SbomUploadProgress(MethodView):
    @auth_required("ASSETS_CREATE")
    def get(self, upload_id: str):
        try:
            upload = accessible_upload(upload_id, current_user)
            refresh_upload(upload)
            return upload_status(upload), 200
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


class WorkerSbomUpload(MethodView):
    @api_key_required
    def get(self, upload_id: str):
        try:
            upload = accessible_upload(upload_id)
            if upload.status not in ("QUEUED", "PROCESSING") or upload.source is None:
                return {"error": "SBOM source is no longer available."}, 409
            upload.status, upload.updated = "PROCESSING", upload.utcnow()
            job = db.session.get(DiscoveryImport, upload_id)
            headers = {"Cache-Control": "no-store"}
            if job:
                headers["X-Discovery-Files"] = "2" if job.second_name else "1"
            raw = job.second_file if job and request.args.get("file") == "2" else upload.source
            if raw is None:
                return {"error": "File unavailable."}, 409
            db.session.commit()
            return Response(raw, mimetype="application/octet-stream", headers=headers)
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status

    @api_key_required
    def post(self, upload_id: str, action: str):
        try:
            upload = accessible_upload(upload_id)
            data = request.get_json(silent=True)
            job = db.session.get(DiscoveryImport, upload_id)
            owner = None
            changed = None
            if action == "discovery" and job:
                prepare_discovery_import(upload, job, PreparedDiscovery.model_validate(data))
            elif action == "begin":
                begin_preview(upload, SbomSummary.model_validate(data))
            elif action == "components":
                persist_batch(upload, SbomComponentBatch.model_validate(data))
            elif action == "findings":
                persist_batch(upload, SbomFindingBatch.model_validate(data))
            elif action == "complete":
                if job and upload.status == "READY":
                    return upload_status(upload), 200
                if not job or (job.prepared or {}).get("sbom_file"):
                    finish_preview(upload)
                elif not job.prepared:
                    raise SbomImportError("Discovery evidence is incomplete.", 409)
                else:
                    upload.status, upload.source = "READY", None
                if job:
                    owner = db.session.get(User, upload.user_id)
                    assert owner is not None
                    changed = apply_discovery(upload, job, owner, {})
                    job.second_file = None
            elif action == "failure":
                # Only a worker's explicitly curated validation message is displayable.
                message = data.get("public_message") if isinstance(data, dict) else None
                if isinstance(message, str) and len(message) <= 500:
                    fail_upload(upload, message)
                else:
                    fail_upload(upload)
            else:
                return {"error": "Unknown SBOM preparation action."}, 404
            upload.updated = upload.utcnow()
            db.session.commit()
            if job and action == "complete":
                invalidate_frontend_cache_on_success(200, models=("asset",))
                if changed:
                    applied_response(changed, True, 200, owner)
            return upload_status(upload), 200
        except ValidationError:
            db.session.rollback()
            return {"error": "Invalid prepared SBOM data."}, 400
        except SbomImportError as exc:
            db.session.rollback()
            return {"error": exc.public_message}, exc.status


class SbomPreview(MethodView):
    @auth_required("ASSETS_CREATE")
    def get(self, import_id: str):
        try:
            return inventory_response(owned_import(import_id, current_user)), 200
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status

    @auth_required("ASSETS_CREATE")
    def post(self, import_id: str):
        try:
            record = owned_import(import_id, current_user)
            if record.asset_id:
                asset = Asset.get(record.asset_id)
                assert asset is not None
                return applied_response(asset, False, 200)
            data = SbomCreateAsset.model_validate(request.get_json(silent=True))
            asset, changed = apply_import(import_id, current_user, create=data)
            return applied_response(asset, changed, 201)
        except ValidationError:
            return {"error": "Provide an asset name (up to 255 characters) and a destination group."}, 400
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


class AssetSbomInventory(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if Asset.get_for_api(asset_id, current_user.organization)[1] != 200:
            return {"error": "Asset not found."}, 404
        if not (record := current_import(asset_id)):
            return {"error": "This asset has no SBOM inventory."}, 404
        try:
            return inventory_response(record), 200
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status

    @auth_required("ASSETS_CREATE")
    def put(self, asset_id: str):
        try:
            data = SbomReplaceAsset.model_validate(request.get_json(silent=True))
            asset, changed = apply_import(
                data.import_id,
                current_user,
                asset_id=asset_id,
                expected_sha256=data.expected_sha256,
                enable_software_matching=data.enable_software_matching,
                enable_cve_matching=data.enable_cve_matching,
            )
            return applied_response(asset, changed, 200)
        except ValidationError:
            return {"error": "Provide a preview import ID and the expected current SBOM hash."}, 400
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


class AssetSbomCveMatching(MethodView):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id: str, cve_id: str):
        if Asset.get_for_api(asset_id, current_user.organization)[1] != 200:
            return {"error": "Asset not found."}, 404
        try:
            data = SbomCveMatching.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide whether CVE matching is enabled."}, 400
        finding = db.session.scalar(
            db.select(AssetSbomFinding)
            .join(AssetSbomImport)
            .where(AssetSbomImport.asset_id == asset_id, AssetSbomFinding.cve_id == normalize_ioc_value(cve_id, "cve"))
        )
        if not finding or not finding.cve_id:
            return {"error": "Imported CVE not found."}, 404
        finding.matching_enabled = data.enabled
        db.session.commit()
        return {"message": "CVE matching updated.", "enabled": data.enabled}, 200


class DiscoveryUpload(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self):
        files = request.files.getlist("file")
        source = request.form.get("source", "").strip()
        if (
            not 1 <= len(files) <= 2
            or not all(f.filename for f in files)
            or (source and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}", source))
        ):
            return {"error": "Select one or two JSON files and a valid inventory source."}, 400
        try:
            upload = stage_discovery(
                [(secure_filename(f.filename or "")[:255] or "inventory.json", f.read()) for f in files], source, current_user
            )
            return {"id": upload.id, "state": "queued"}, 202
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


def discovery_receipt(upload_id, *, read_completed=False):
    upload = accessible_upload(upload_id, current_user, read_completed=read_completed)
    job = db.session.get(DiscoveryImport, upload_id)
    if not job:
        raise SbomImportError("Discovery import unavailable.", 404)
    refresh_upload(upload)
    assets = job.result.get("assets", [])
    if any(Asset.get_for_api(a["id"], current_user.organization)[1] != 200 for a in assets):
        raise SbomImportError("Discovery import unavailable.", 404)
    if job.result.get("reason") in ("identity", "scope") and any(
        not a.get("id") or Asset.get_for_api(a["id"], current_user.organization)[1] != 200 for a in job.result["options"]
    ):
        raise SbomImportError("Discovery import unavailable.", 404)
    if job.result.get("reason") == "destination" and any(
        not AssetGroup.access_allowed(current_user.organization, g["id"]) for g in job.result["groups"]
    ):
        raise SbomImportError("Discovery import unavailable.", 404)
    return upload, job


class DiscoveryProgress(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, upload_id):
        try:
            upload, job = discovery_receipt(upload_id, read_completed=True)
            return {"id": upload_id, "source": job.source, "state": upload.status.lower(), "message": upload.error, **job.result}, 200
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status

    @auth_required("ASSETS_ACCESS")
    @auth_required("ASSETS_CREATE")
    def post(self, upload_id):
        try:
            upload, job = discovery_receipt(upload_id)
            if job.result.get("state") != "review":
                raise SbomImportError("This import has no decision pending.", 409)
            choice = request.get_json(silent=True)
            field = {"destination": "group_id", "scope": "scope", "identity": "asset_id", "replacement": "expected_sha256"}.get(
                job.result.get("reason", "")
            )
            if not field or not isinstance(choice, dict) or set(choice) != {field} or not isinstance(choice[field], str):
                raise SbomImportError("Invalid import decision.", 400)
            changed = apply_discovery(upload, job, current_user, choice)
            db.session.commit()
            invalidate_frontend_cache_on_success(200, models=("asset",))
            if changed:
                applied_response(changed, True, 200)
            return {"id": upload_id, **job.result}, 200
        except SbomImportError as exc:
            db.session.rollback()
            return {"error": exc.public_message}, exc.status


class AssetServices(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id):
        try:
            return asset_services(asset_id, current_user), 200
        except SbomImportError as exc:
            return {"error": exc.public_message}, exc.status


def initialize(app, base_route: str):
    app.add_url_rule(f"{base_route}/assets/discovery-imports", view_func=DiscoveryUpload.as_view("discovery_upload"))
    app.add_url_rule(f"{base_route}/assets/discovery-imports/<string:upload_id>", view_func=DiscoveryProgress.as_view("discovery_progress"))
    app.add_url_rule(f"{base_route}/assets/<string:asset_id>/services", view_func=AssetServices.as_view("asset_services"))
    app.add_url_rule(f"{base_route}/assets/sbom-uploads/<string:upload_id>", view_func=SbomUploadProgress.as_view("sbom_upload_progress"))
    worker_view = WorkerSbomUpload.as_view("worker_sbom_upload")
    app.add_url_rule(f"{base_route}/worker/sbom-uploads/<string:upload_id>", view_func=worker_view, methods=["GET"])
    app.add_url_rule(f"{base_route}/worker/sbom-uploads/<string:upload_id>/<string:action>", view_func=worker_view, methods=["POST"])
    app.add_url_rule(f"{base_route}/assets/sbom-imports", view_func=SbomUpload.as_view("sbom_upload"))
    app.add_url_rule(f"{base_route}/assets/sbom-imports/<string:import_id>", view_func=SbomPreview.as_view("sbom_preview"))
    app.add_url_rule(f"{base_route}/assets/<string:asset_id>/sbom", view_func=AssetSbomInventory.as_view("asset_sbom"))
    app.add_url_rule(
        f"{base_route}/assets/<string:asset_id>/sbom/cves/<string:cve_id>", view_func=AssetSbomCveMatching.as_view("asset_sbom_cve")
    )
