"""Asset CVE inventory pages with current permissions and uncached counts."""

from flask import render_template, request, url_for
from models.asset_cve import CVE_SEVERITIES, AssetCve, AssetCveList, AssetCveOverview, AssetCveSummary
from requests import RequestException

from frontend.auth import auth_required
from frontend.cache_models import CacheObject
from frontend.core_api import CoreApi
from frontend.log import logger


@auth_required("ASSETS_ACCESS")
def asset_cves(asset_id: str | None = None):
    api = CoreApi()
    endpoint = f"/assets/{asset_id}/cves" if asset_id else "/assets/cves"
    data, pagination, error, status = None, None, None, 200
    try:
        # Inventory replacement and manual edits must be reflected on the next read.
        response = api.session.get(f"{api.api_url}{endpoint}", params=request.args, timeout=api.timeout)
        if response.ok:
            model = AssetCveList if asset_id else AssetCveOverview
            data = model.model_validate(response.json())
            pagination = CacheObject[AssetCve | AssetCveSummary](
                list(data.items), page=data.page, limit=data.limit, total_count=data.total_count
            )
        else:
            error, status = "Unable to load asset CVEs.", response.status_code
    except RequestException, ValueError:
        logger.exception("Asset CVE read failed")
        error, status = "Unable to load asset CVEs. Please try again.", 502
    base_url = url_for("assets.asset_cves", asset_id=asset_id) if asset_id else url_for("assets.assets_cves")
    return render_template(
        "assets/cves.html",
        asset_id=asset_id,
        data=data,
        pagination=pagination,
        base_url=base_url,
        severities=CVE_SEVERITIES,
        error=error,
    ), status
