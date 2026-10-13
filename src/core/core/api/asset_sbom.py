"""User-scoped SBOM previews, replacement, and imported CVE matching decisions."""

from math import ceil

from flask import request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.cti import normalize_ioc_value
from models.sbom import SbomCreateAsset, SbomCveMatching, SbomInventory, SbomReplaceAsset
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from core.managers.auth_manager import auth_required
from core.managers.db_manager import db
from core.model.asset import Asset
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFinding, AssetSbomImport
from core.service.asset_intelligence import start_match_run, trigger_suggestions
from core.service.asset_sbom import SbomImportError, apply_import, compare_import, create_preview, current_import, owned_import
from core.service.cache_invalidation import invalidate_frontend_cache_on_success
from core.service.sbom import SbomValidationError


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


def applied_response(asset: Asset, changed: bool, status: int):
    if changed:
        invalidate_frontend_cache_on_success(status, models=("asset",), object_ids={"asset": asset.id})
        if {"ASSETS_ACCESS", "ASSESS_ACCESS"}.issubset(current_user.get_permissions()):
            start_match_run(asset.id, current_user)
    return {"id": asset.id, "message": "SBOM applied." if changed else "This SBOM has already been applied."}, status if changed else 200


class SbomUpload(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self):
        upload = request.files.get("file")
        if not upload:
            return {"error": "Select a CycloneDX JSON file."}, 400
        try:
            record, created = create_preview(
                upload.read(),
                secure_filename(upload.filename or "sbom.json")[:255] or "sbom.json",
                current_user,
                asset_id=request.args.get("asset_id") or None,
            )
            return inventory_response(record), 201 if created else 200
        except SbomValidationError as exc:
            return {"error": exc.public_message}, 400
        except SbomImportError as exc:
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
            asset, changed = apply_import(data.import_id, current_user, asset_id=asset_id, expected_sha256=data.expected_sha256)
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


def initialize(app, base_route: str):
    app.add_url_rule(f"{base_route}/assets/sbom-imports", view_func=SbomUpload.as_view("sbom_upload"))
    app.add_url_rule(f"{base_route}/assets/sbom-imports/<string:import_id>", view_func=SbomPreview.as_view("sbom_preview"))
    app.add_url_rule(f"{base_route}/assets/<string:asset_id>/sbom", view_func=AssetSbomInventory.as_view("asset_sbom"))
    app.add_url_rule(
        f"{base_route}/assets/<string:asset_id>/sbom/cves/<string:cve_id>", view_func=AssetSbomCveMatching.as_view("asset_sbom_cve")
    )
