"""Live trigger review and intelligence evidence; permissions are rechecked by Core."""

from flask import redirect, render_template, request, url_for
from requests import RequestException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.log import logger


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
    return render_template("assets/triggers.html", asset_id=asset_id, data=data, error=error), status


@auth_required("ASSETS_ACCESS")
def asset_intelligence(asset_id: str):
    api = CoreApi()
    error, status = None, 200
    data, run = None, None
    try:
        if request.method == "POST":
            response = api.api_post(f"/assets/{asset_id}/match-runs", {"days": request.form.get("days", "30")})
            if response.ok:
                return redirect(url_for("assets.asset_intelligence", asset_id=asset_id), code=303)
            error, status = response.json().get("error", "Unable to start the scan."), response.status_code
        response = api.session.get(f"{api.api_url}/assets/{asset_id}/intelligence", params=request.args, timeout=api.timeout)
        if response.ok:
            data = response.json()
            response = api.session.get(f"{api.api_url}/assets/{asset_id}/match-runs", timeout=api.timeout)
            if response.ok:
                run = response.json()["run"]
            else:
                error, status = "Unable to load scan status.", response.status_code
        else:
            error, status = response.json().get("error", "Intelligence unavailable."), response.status_code
    except RequestException, ValueError:
        logger.exception("Asset intelligence failed")
        error, status = "Unable to load intelligence. Please try again.", 502
    return render_template("assets/intelligence.html", asset_id=asset_id, data=data, run=run, error=error), status
