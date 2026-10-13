"""Upload once, review a server-owned preview, then create an asset."""

from flask import redirect, render_template, request, url_for
from flask_jwt_extended import current_user
from models.asset import AssetGroup
from models.sbom import SbomInventory
from requests import RequestException

from frontend.auth import auth_required
from frontend.cache_models import PagingData
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger


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
                    return redirect(url_for("assets.sbom_preview", import_id=payload["id"], asset_id=target_id or None), code=303)
                error, status = payload.get("error", "Unable to preview this SBOM."), response.status_code
            except RequestException, ValueError:
                logger.exception("SBOM upload failed")
                error, status = "Unable to upload the SBOM. Please try again.", 502
    return render_template("assets/sbom_upload.html", error=error, target_asset_id=target_id), status


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
            return render_template("assets/sbom_upload.html", error=payload.get("error", "Preview unavailable.")), response.status_code
        if payload.get("asset_id") and not target_id:
            return redirect(url_for(destination, asset_id=payload["asset_id"]), code=303)
        return _render_inventory(payload, preview=True, error=error, status=status)
    except RequestException, ValueError:
        logger.exception("SBOM preview failed")
        return render_template("assets/sbom_upload.html", error="Unable to load the SBOM preview. Please try again."), 502


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
            return render_template(
                "assets/sbom_upload.html", error=payload.get("error", "Inventory unavailable."), read_only=True
            ), response.status_code
        return _render_inventory(payload)
    except RequestException, ValueError:
        logger.exception("SBOM inventory failed")
        return render_template("assets/sbom_upload.html", error="Unable to load the inventory. Please try again.", read_only=True), 502
