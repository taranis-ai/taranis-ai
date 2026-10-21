"""Review shared software rules and asset scan progress using current Core permissions."""

from flask import redirect, render_template, request, url_for
from flask_jwt_extended import current_user
from requests import RequestException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.utils.router_helpers import get_assess_return_url


def save_trigger_form(api: CoreApi, asset_id: str):
    endpoint = f"/assets/{asset_id}/triggers"
    action = request.form.get("action")
    if action == "generate":
        return api.api_post(f"{endpoint}/suggestions", {})
    if action == "selection":
        return api.api_post(
            f"{endpoint}/selection",
            {
                "trigger_ids": request.form.getlist("trigger_ids"),
                "enabled": request.form.get("enabled") == "true",
            },
        )
    data = {
        "phrase": request.form.get("phrase", ""),
        "context": request.form.get("context", "").splitlines(),
        "enabled": request.form.get("enabled") == "on",
    }
    if action == "create":
        return api.api_post(endpoint, {**data, "component_id": request.form.get("component_id", "")})
    if action == "edit" and request.form.get("trigger_id"):
        return api.api_put(f"{endpoint}/{request.form['trigger_id']}", data)
    return None


@auth_required("ASSETS_ACCESS")
def asset_triggers(asset_id: str):
    api = CoreApi()
    error, status = None, 200
    data = None
    try:
        if request.method == "POST":
            response = save_trigger_form(api, asset_id)
            if response is None:
                error, status = "Choose a trigger action.", 400
            elif response.ok:
                return redirect(
                    url_for(
                        "assets.asset_triggers",
                        asset_id=asset_id,
                        assess_url=get_assess_return_url(),
                        page=request.args.get("page", 1),
                        search=request.args.get("search", ""),
                        enabled=request.args.get("enabled", ""),
                        component_id=request.args.get("component_id", ""),
                    ),
                    code=303,
                )
            else:
                error, status = response.json().get("error", "Unable to save triggers."), response.status_code
        # Avoid cached evidence and permission decisions throughout this review workflow.
        response = api.session.get(f"{api.api_url}/assets/{asset_id}/triggers", params=request.args, timeout=api.timeout)
        if response.ok:
            data = response.json()
        else:
            error, status = response.json().get("error", "Triggers unavailable."), response.status_code
    except RequestException, ValueError:
        logger.exception("Asset trigger review failed")
        error, status = "Unable to load or save triggers. Please try again.", 502
    run, scan_error = load_scan_status(asset_id) if "ASSESS_ACCESS" in current_user.permissions else (None, None)
    return render_template("assets/triggers.html", asset_id=asset_id, data=data, error=error or scan_error, run=run), status


def load_scan_status(asset_id: str) -> tuple[dict | None, str | None]:
    try:
        api = CoreApi()
        response = api.session.get(f"{api.api_url}/assets/{asset_id}/match-runs", timeout=api.timeout)
        if response.ok:
            return response.json()["run"], None
    except RequestException, ValueError:
        logger.exception("Asset scan status unavailable")
    return None, "Unable to load scan status."


@auth_required("ASSETS_ACCESS")
def asset_scan(asset_id: str):
    if request.method == "GET":
        run, error = load_scan_status(asset_id)
        return render_template("assets/scan_status.html", asset_id=asset_id, run=run, scan_error=error), 502 if error else 200
    try:
        response = CoreApi().api_post(f"/assets/{asset_id}/match-runs", {"days": request.form.get("days", "30")})
        if response.ok:
            return redirect(url_for("assets.asset_triggers", asset_id=asset_id, assess_url=get_assess_return_url()), code=303)
        error, status = "Unable to start the scan. Check that software rules are enabled and the lookback is valid.", response.status_code
    except RequestException:
        logger.exception("Unable to start asset scan")
        error, status = "Unable to start the scan. Please try again.", 502
    return render_template("assets/scan_error.html", asset_id=asset_id, error=error), status
