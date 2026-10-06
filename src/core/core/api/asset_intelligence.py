"""Asset-scoped trigger review and explainable intelligence matching."""

from flask import request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.asset_intelligence import MatchRunInput, TriggerCreate, TriggerInput, TriggerSelection
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from core.managers import queue_manager
from core.managers.auth_manager import api_key_required, auth_required
from core.managers.db_manager import db
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent
from core.service.asset_intelligence import (
    accessible_asset,
    asset_components,
    asset_triggers,
    generate_triggers,
    relevant_stories,
    scan_batch,
)


TRIGGERS_PER_PAGE = 50


def trigger_response(trigger: AssetTrigger) -> dict:
    component = trigger.component.inventory
    return {
        "id": trigger.id,
        "component_id": trigger.component_id,
        "component": component["name"],
        "version": component["version"],
        "purl": component["purl"],
        "has_cpe": bool(component["cpes"]),
        "phrase": trigger.phrase,
        "context": trigger.context,
        "enabled": trigger.enabled,
        "sources": trigger.sources,
        "analyst_edited": trigger.analyst_edited,
    }


def run_response(run: AssetMatchRun) -> dict:
    return {"id": run.id, "status": run.status, "days": run.days, "processed": run.processed, "error": run.error}


class AssetTriggers(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if not (asset := accessible_asset(asset_id, current_user)):
            return {"error": "Asset not found."}, 404
        query = asset_triggers(asset_id)
        if component_id := request.args.get("component_id"):
            query = query.where(AssetTrigger.component_id == component_id)
        if search := request.args.get("search", "").strip():
            query = query.where(AssetTrigger.phrase.icontains(search, autoescape=True))
        if request.args.get("enabled") in ("true", "false"):
            query = query.where(AssetTrigger.enabled.is_(request.args["enabled"] == "true"))
        total = db.session.scalar(db.select(func.count()).select_from(query.subquery())) or 0
        pages = max(1, (total + TRIGGERS_PER_PAGE - 1) // TRIGGERS_PER_PAGE)
        page = min(pages, max(1, request.args.get("page", 1, type=int)))
        triggers = db.session.scalars(
            query.options(selectinload(AssetTrigger.component))
            .order_by(AssetTrigger.phrase, AssetTrigger.id)
            .offset((page - 1) * TRIGGERS_PER_PAGE)
            .limit(TRIGGERS_PER_PAGE)
        )
        return {"asset_name": asset.name, "items": [trigger_response(t) for t in triggers], "page": page, "pages": pages, "total": total}, 200

    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        try:
            data = TriggerCreate.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide a component, a phrase up to 200 characters and at most 10 context phrases."}, 400
        if not db.session.scalar(asset_components(asset_id).where(AssetSbomComponent.id == data.component_id)):
            return {"error": "Component not found in this asset."}, 404
        trigger = AssetTrigger(data.component_id, data.phrase, data.context, ["analyst"], enabled=data.enabled)
        trigger.analyst_edited = True
        db.session.add(trigger)
        db.session.commit()
        return trigger_response(trigger), 201


class AssetTriggerEdit(MethodView):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id: str, trigger_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        trigger = db.session.scalar(asset_triggers(asset_id).where(AssetTrigger.id == trigger_id).with_for_update())
        if not trigger:
            return {"error": "Trigger not found."}, 404
        try:
            data = TriggerInput.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide a phrase up to 200 characters and at most 10 context phrases."}, 400
        trigger.phrase, trigger.context, trigger.enabled = data.phrase, data.context, data.enabled
        trigger.analyst_edited = True
        db.session.execute(db.delete(AssetArticleMatch).where(AssetArticleMatch.trigger_id == trigger.id))
        db.session.commit()
        return trigger_response(trigger), 200


class AssetTriggerSelection(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        try:
            data = TriggerSelection.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Select between 1 and 100 triggers and whether to enable them."}, 400
        triggers = list(db.session.scalars(asset_triggers(asset_id).where(AssetTrigger.id.in_(data.trigger_ids)).with_for_update()))
        if len(triggers) != len(set(data.trigger_ids)):
            return {"error": "A selected trigger does not belong to this asset."}, 404
        for trigger in triggers:
            trigger.enabled = data.enabled
            trigger.analyst_edited = True
        if not data.enabled:
            db.session.execute(db.delete(AssetArticleMatch).where(AssetArticleMatch.trigger_id.in_(data.trigger_ids)))
        db.session.commit()
        return {"message": "Selected triggers updated."}, 200


class AssetTriggerSuggestions(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        added = generate_triggers(asset_id)
        db.session.commit()
        return {"message": "Missing suggestions generated. Existing decisions preserved.", "added": added}, 200


class AssetIntelligence(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if "ASSESS_ACCESS" not in current_user.get_permissions():
            return {"error": "Intelligence access is required."}, 403
        if not (asset := accessible_asset(asset_id, current_user)):
            return {"error": "Asset not found."}, 404
        page = max(1, request.args.get("page", 1, type=int))
        return {"asset_name": asset.name, **relevant_stories(asset_id, current_user, page)}, 200


class AssetMatchRuns(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if "ASSESS_ACCESS" not in current_user.get_permissions():
            return {"error": "Intelligence access is required."}, 403
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        run = db.session.scalar(
            db.select(AssetMatchRun)
            .filter_by(asset_id=asset_id, user_id=current_user.id)
            .order_by(AssetMatchRun.created.desc(), AssetMatchRun.id.desc())
            .limit(1)
        )
        return {"run": run_response(run) if run else None}, 200

    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if "ASSESS_ACCESS" not in current_user.get_permissions():
            return {"error": "Intelligence access is required."}, 403
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        try:
            data = MatchRunInput.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Choose a collection lookback between 0 (all history) and 36500 days."}, 400
        if not db.session.scalar(asset_triggers(asset_id).where(AssetTrigger.enabled.is_(True)).limit(1)):
            return {"error": "Enable at least one trigger before scanning."}, 400
        manager = queue_manager.queue_manager
        if error := manager.queue_action_error():
            return error
        run = AssetMatchRun(asset_id, current_user.id, data.days)
        db.session.add(run)
        db.session.commit()
        job = manager.enqueue_task(
            "misc",
            "asset_match_task",
            run.id,
            job_id=run.id,
            job_timeout=1800,
            meta={"task": "asset_match_task", "user_id": current_user.id, "worker_id": asset_id, "worker_type": "asset_match_task"},
        )
        if not job:
            run.status, run.error = "FAILED", "Unable to queue the scan. Please try again."
            db.session.commit()
            return {"error": run.error}, 503
        return run_response(run), 202


class AssetMatchBatch(MethodView):
    @api_key_required
    def post(self, run_id: str):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"error": "Provide a JSON object."}, 400
        run = db.session.scalar(db.select(AssetMatchRun).filter_by(id=run_id).with_for_update())
        if not run:
            return {"error": "Matching run not found."}, 404
        if run.status not in ("COMPLETED", "FAILED"):
            if data.get("failed") is True:
                run.status, run.error = "FAILED", "The scan could not finish. Please start another scan."
            else:
                scan_batch(run)
            db.session.commit()
        return run_response(run), 200


def initialize(app, base_route: str):
    routes = {
        "triggers": AssetTriggers,
        "triggers/<string:trigger_id>": AssetTriggerEdit,
        "triggers/selection": AssetTriggerSelection,
        "triggers/suggestions": AssetTriggerSuggestions,
        "intelligence": AssetIntelligence,
        "match-runs": AssetMatchRuns,
    }
    for suffix, view in routes.items():
        app.add_url_rule(f"{base_route}/assets/<string:asset_id>/{suffix}", view_func=view.as_view(view.__name__))
    app.add_url_rule(f"{base_route}/worker/asset-match-runs/<string:run_id>/batch", view_func=AssetMatchBatch.as_view("asset_match_batch"))
