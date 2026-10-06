"""User-scoped SBOM previews and atomic asset creation."""

import hashlib
from datetime import timedelta
from math import ceil

from flask import request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.sbom import SbomCreateAsset, SbomInventory
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from core.managers.auth_manager import auth_required
from core.managers.db_manager import db
from core.model.asset import Asset, AssetCpe, AssetGroup
from core.model.asset_sbom import AssetSbomComponent, AssetSbomImport
from core.service.asset_intelligence import generate_triggers, trigger_suggestions
from core.service.cache_invalidation import invalidate_frontend_cache_on_success
from core.service.sbom import SbomValidationError, parse_sbom


PREVIEW_LIFETIME = timedelta(hours=24)
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
    return SbomInventory(
        id=record.id,
        asset_id=record.asset_id,
        filename=record.filename,
        sha256=record.sha256,
        imported_at=record.serialize_datetime(record.confirmed or record.created),
        summary=record.summary,
        components=[
            {**component.inventory, "id": component.id, "suggestions": trigger_suggestions(component.inventory)} for component in components
        ],
        page=page,
        pages=pages,
    ).model_dump(mode="json")


def get_owned_import(import_id: str, *, lock: bool = False) -> AssetSbomImport | None:
    query = db.select(AssetSbomImport).filter_by(
        id=import_id,
        user_id=current_user.id,
        organization_id=current_user.organization.id,
    )
    if lock:
        query = query.with_for_update()
    record = db.session.scalar(query)
    if not record or (not record.asset_id and record.created < record.utcnow() - PREVIEW_LIFETIME):
        return None
    if record.asset_id and Asset.get_for_api(record.asset_id, current_user.organization)[1] != 200:
        return None
    return record


class SbomUpload(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self):
        upload = request.files.get("file")
        if not upload:
            return {"error": "Select a CycloneDX JSON file."}, 400
        raw = upload.read()
        try:
            summary, components = parse_sbom(raw)
        except SbomValidationError as exc:
            # Only this domain exception contains deliberately curated public text.
            return {"error": exc.public_message}, 400
        digest = hashlib.sha256(raw).hexdigest()
        # Resume this user's existing preview instead of storing another copy on retry.
        previous = db.session.scalar(
            db.select(AssetSbomImport)
            .filter_by(
                sha256=digest,
                user_id=current_user.id,
                organization_id=current_user.organization.id,
            )
            .order_by(AssetSbomImport.created.desc())
            .limit(1)
        )
        if previous and get_owned_import(previous.id):
            return inventory_response(previous), 200
        db.session.execute(
            db.delete(AssetSbomImport).where(
                AssetSbomImport.asset_id.is_(None),
                AssetSbomImport.created < AssetSbomImport.utcnow() - PREVIEW_LIFETIME,
            )
        )
        record = AssetSbomImport(
            filename=secure_filename(upload.filename or "sbom.json")[:255] or "sbom.json",
            sha256=digest,
            user_id=current_user.id,
            organization_id=current_user.organization.id,
            summary=summary.model_dump(),
        )
        record.components = [AssetSbomComponent(position=i, inventory=c.model_dump()) for i, c in enumerate(components)]
        db.session.add(record)
        db.session.commit()
        return inventory_response(record), 201


class SbomPreview(MethodView):
    @auth_required("ASSETS_CREATE")
    def get(self, import_id: str):
        if not (record := get_owned_import(import_id)):
            return {"error": "SBOM preview unavailable or expired. Upload the file again."}, 404
        return inventory_response(record), 200

    @auth_required("ASSETS_CREATE")
    def post(self, import_id: str):
        if not (record := get_owned_import(import_id, lock=True)):
            return {"error": "SBOM preview unavailable or expired. Upload the file again."}, 404
        if record.asset_id:
            return {"id": record.asset_id, "message": "This SBOM has already been imported."}, 200
        try:
            data = SbomCreateAsset.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide an asset name (up to 255 characters) and a destination group."}, 400
        if not data.name.strip():
            return {"error": "Provide an asset name."}, 400
        group = AssetGroup.get(data.asset_group_id)
        if not group or not AssetGroup.access_allowed(current_user.organization, group.id):
            return {"error": "Asset group unavailable."}, 403
        # A conditional write also serializes double submissions on SQLite, which ignores FOR UPDATE.
        claimed = db.session.scalar(
            db.update(AssetSbomImport)
            .where(AssetSbomImport.id == record.id, AssetSbomImport.confirmed.is_(None))
            .values(confirmed=record.utcnow())
            .returning(AssetSbomImport.id)
        )
        if not claimed:
            db.session.refresh(record)
            return {"id": record.asset_id, "message": "This SBOM has already been imported."}, 200
        asset = Asset(name=data.name.strip(), serial="", description=data.description, group=group)
        cpes = {cpe for component in record.components for cpe in component.inventory["cpes"]}
        asset.asset_cpes = [AssetCpe(cpe) for cpe in sorted(cpes)]
        db.session.add(asset)
        db.session.flush()
        record.asset_id = asset.id
        db.session.flush()
        generate_triggers(asset.id)
        asset.update_vulnerabilities()
        db.session.commit()
        invalidate_frontend_cache_on_success(201, models=("asset",))
        return {"id": asset.id, "message": "Asset created from SBOM."}, 201


class AssetSbomInventory(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if Asset.get_for_api(asset_id, current_user.organization)[1] != 200:
            return {"error": "Asset not found."}, 404
        record = db.session.scalar(db.select(AssetSbomImport).filter_by(asset_id=asset_id))
        if not record:
            return {"error": "This asset has no SBOM inventory."}, 404
        return inventory_response(record), 200


def initialize(app, base_route: str):
    app.add_url_rule(f"{base_route}/assets/sbom-imports", view_func=SbomUpload.as_view("sbom_upload"))
    app.add_url_rule(f"{base_route}/assets/sbom-imports/<string:import_id>", view_func=SbomPreview.as_view("sbom_preview"))
    app.add_url_rule(f"{base_route}/assets/<string:asset_id>/sbom", view_func=AssetSbomInventory.as_view("asset_sbom"))
