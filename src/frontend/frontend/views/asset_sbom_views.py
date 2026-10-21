"""Queue preparation, review the private preview, then create or update an asset."""

from flask import redirect, render_template, request, url_for
from flask_jwt_extended import current_user
from models.asset import AssetGroup
from models.sbom import SbomInventory, SbomUploadStatus
from requests import RequestException

from frontend.auth import auth_required
from frontend.cache_models import PagingData
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.views.asset_views import asset_display_name


def _matching_choices() -> dict[str, bool]:
    return {key: request.method != "POST" or request.form.get(key) == "on" for key in ("enable_software_matching", "enable_cve_matching")}


def _render_upload(*, target_id=None, error=None, status=200, read_only=False):
    return render_template(
        "assets/sbom_upload.html",
        target_asset_id=target_id,
        asset_name=asset_display_name(target_id),
        error=error,
        read_only=read_only,
    ), status


def _render_inventory(payload, *, preview=False, error=None, status=200):
    inventory = SbomInventory.model_validate(payload)
    groups = DataPersistenceLayer().get_objects(AssetGroup, PagingData().set_fetch_all()) if preview else []
    return render_template(
        "assets/sbom_inventory.html",
        inventory=inventory,
        preview=preview,
        groups=groups,
        error=error,
        name=request.form.get("name", inventory.summary.suggested_name),
        tags_text=request.form.get("tags_text", ""),
        group_id=request.form.get("asset_group_id", ""),
        description=request.form.get("description", inventory.summary.description[:10000]),
        asset_name=inventory.comparison.asset_name if inventory.comparison else asset_display_name(inventory.asset_id),
        **_matching_choices(),
    ), status


@auth_required("ASSETS_CREATE")
def upload_sbom():
    error = None
    status = 200
    target_id = request.args.get("asset_id", "")
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            error, status = "Select a CycloneDX JSON file.", 400
        else:
            try:
                response = CoreApi().upload_sbom(upload, asset_id=target_id or None)
                payload = response.json()
                if response.ok:
                    return redirect(url_for("assets.sbom_progress", upload_id=payload["id"], asset_id=target_id or None), code=303)
                error, status = payload.get("error", "Unable to preview this SBOM."), response.status_code
            except RequestException, ValueError:
                logger.exception("SBOM upload failed")
                error, status = "Unable to upload the SBOM. Please try again.", 502
    return _render_upload(target_id=target_id, error=error, status=status)


@auth_required("ASSETS_CREATE")
def sbom_progress(upload_id: str):
    api = CoreApi()
    target_id = request.args.get("asset_id")
    progress = None
    error, status = None, 200
    try:
        response = api.session.get(f"{api.api_url}/assets/sbom-uploads/{upload_id}", timeout=api.timeout)
        if not response.ok:
            error, status = "SBOM processing status unavailable.", response.status_code
        else:
            progress = SbomUploadStatus.model_validate(response.json())
            target_id = progress.target_asset_id
            if progress.status == "READY" and progress.import_id:
                target = url_for("assets.sbom_preview", import_id=progress.import_id, asset_id=target_id)
                if request.headers.get("HX-Request"):
                    return "", 200, {"HX-Redirect": target}
                return redirect(target, code=303)
    except RequestException, ValueError:
        logger.exception("SBOM processing status unavailable")
        error, status = "Unable to load SBOM processing status. Please reload this page.", 502
    return render_template(
        "assets/sbom_progress.html",
        progress=progress,
        upload_id=upload_id,
        target_asset_id=target_id,
        asset_name=asset_display_name(target_id),
        error=error,
    ), status


@auth_required("ASSETS_CREATE")
def preview_sbom(import_id: str):
    api = CoreApi()
    target_id = request.args.get("asset_id", "")
    error = None
    status = 200
    destination = "assets.asset_intelligence" if "ASSESS_ACCESS" in current_user.permissions else "assets.asset_sbom"
    try:
        if request.method == "POST":
            if target_id:
                response = api.api_put(
                    f"/assets/{target_id}/sbom",
                    {
                        "import_id": import_id,
                        "expected_sha256": request.form.get("expected_sha256") or None,
                        **_matching_choices(),
                    },
                )
            else:
                response = api.api_post(
                    f"/assets/sbom-imports/{import_id}",
                    {
                        "name": request.form.get("name", ""),
                        "asset_group_id": request.form.get("asset_group_id", ""),
                        "description": request.form.get("description", ""),
                        "tags": request.form.get("tags_text", "").splitlines(),
                        **_matching_choices(),
                    },
                )
            payload = response.json()
            if response.ok:
                return redirect(url_for(destination, asset_id=payload["id"]), code=303)
            error, status = payload.get("error", "Unable to create the asset."), response.status_code
        # Previews must always reflect current ownership and confirmation state.
        response = api.session.get(
            f"{api.api_url}/assets/sbom-imports/{import_id}",
            params={"page": request.args.get("page", 1), "asset_id": target_id},
            timeout=api.timeout,
        )
        payload = response.json()
        if not response.ok:
            return _render_upload(target_id=target_id, error=payload.get("error", "Preview unavailable."), status=response.status_code)
        if payload.get("asset_id") and not target_id:
            return redirect(url_for(destination, asset_id=payload["asset_id"]), code=303)
        return _render_inventory(payload, preview=True, error=error, status=status)
    except RequestException, ValueError:
        logger.exception("SBOM preview failed")
        return _render_upload(target_id=target_id, error="Unable to load the SBOM preview. Please try again.", status=502)


@auth_required("ASSETS_ACCESS")
def asset_inventory(asset_id: str):
    api = CoreApi()
    try:
        response = api.session.get(
            f"{api.api_url}/assets/{asset_id}/sbom",
            params={"page": request.args.get("page", 1)},
            timeout=api.timeout,
        )
        payload = response.json()
        if not response.ok:
            return _render_upload(
                target_id=asset_id, error=payload.get("error", "Inventory unavailable."), read_only=True, status=response.status_code
            )
        return _render_inventory(payload)
    except RequestException, ValueError:
        logger.exception("SBOM inventory failed")
        return _render_upload(target_id=asset_id, error="Unable to load the inventory. Please try again.", read_only=True, status=502)
