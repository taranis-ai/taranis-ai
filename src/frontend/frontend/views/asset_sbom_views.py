"""Upload once, review a server-owned preview, then create an asset."""

from flask import redirect, render_template, request, url_for
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
        group_id=request.form.get("asset_group_id", ""),
        description=request.form.get("description", ""),
    ), status


@auth_required("ASSETS_CREATE")
def upload_sbom():
    error = None
    status = 200
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            error, status = "Select a CycloneDX JSON file.", 400
        else:
            try:
                response = CoreApi().upload_sbom(upload)
                payload = response.json()
                if response.ok:
                    return redirect(url_for("assets.sbom_preview", import_id=payload["id"]), code=303)
                error, status = payload.get("error", "Unable to preview this SBOM."), response.status_code
            except RequestException, ValueError:
                logger.exception("SBOM upload failed")
                error, status = "Unable to upload the SBOM. Please try again.", 502
    return render_template("assets/sbom_upload.html", error=error), status


@auth_required("ASSETS_CREATE")
def preview_sbom(import_id: str):
    api = CoreApi()
    error = None
    status = 200
    try:
        if request.method == "POST":
            response = api.api_post(
                f"/assets/sbom-imports/{import_id}",
                {
                    "name": request.form.get("name", ""),
                    "asset_group_id": request.form.get("asset_group_id", ""),
                    "description": request.form.get("description", ""),
                },
            )
            payload = response.json()
            if response.ok:
                return redirect(url_for("assets.asset_sbom", asset_id=payload["id"]), code=303)
            error, status = payload.get("error", "Unable to create the asset."), response.status_code
        # Previews must always reflect current ownership, expiry and confirmation state.
        response = api.session.get(
            f"{api.api_url}/assets/sbom-imports/{import_id}",
            params={"page": request.args.get("page", 1)},
            timeout=api.timeout,
        )
        payload = response.json()
        if not response.ok:
            return render_template("assets/sbom_upload.html", error=payload.get("error", "Preview unavailable.")), response.status_code
        if payload.get("asset_id"):
            return redirect(url_for("assets.asset_sbom", asset_id=payload["asset_id"]), code=303)
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
