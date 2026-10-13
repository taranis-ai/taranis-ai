"""Asset trigger review and explainable intelligence for one or all accessible hosts."""

from flask import request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.asset_intelligence import IntelligenceFilters, MatchRunInput, TriggerCreate, TriggerInput, TriggerSelection
from pydantic import ValidationError

from core.managers.auth_manager import api_key_required, auth_required
from core.managers.db_manager import db
from core.model.asset import Asset
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent
from core.service.asset_intelligence import (
    accessible_asset,
    asset_components,
    asset_triggers,
    generate_triggers,
    grouped_triggers,
    product_identity,
    scan_batch,
    start_match_run,
)
from core.service.asset_intelligence_overview import intelligence_overview


TRIGGERS_PER_PAGE = 50
INTELLIGENCE_FILTER_ERROR = (
    "Choose Any, Yes or No for match filters, a positive page, 1–100 stories per page, a complete CVE ID, "
    "CVSS scores from 0 to 10 with minimum ≤ maximum, and collection dates with start ≤ end."
)


def trigger_response(trigger: AssetTrigger, group: list[AssetTrigger] | None = None) -> dict:
    component = trigger.component.inventory
    group = group or [trigger]
    return {
        "id": trigger.id,
        "component_id": trigger.component_id,
        "component": component["name"],
        "version": component["version"],
        "versions": sorted({t.component.inventory["version"] for t in group}),
        "component_ids": [t.component_id for t in group],
        "purl": component["purl"],
        "has_cpe": bool(component["cpes"]),
        "phrase": trigger.phrase,
        "context": trigger.context,
        "enabled": trigger.enabled,
        "sources": trigger.sources,
        "analyst_edited": trigger.analyst_edited,
        "review_required": any(
            (t.suggestion or f"analyst:{t.phrase.casefold()}") in t.component.inventory.get("review_conflicts", []) for t in group
        ),
    }


def resolve_inheritance_review(trigger: AssetTrigger) -> None:
    component = trigger.component
    key = trigger.suggestion or f"analyst:{trigger.phrase.casefold()}"
    conflicts = component.inventory.get("review_conflicts", [])
    if key in conflicts:
        component.inventory = {**component.inventory, "review_conflicts": [value for value in conflicts if value != key]}


def run_response(run: AssetMatchRun) -> dict:
    return {"id": run.id, "status": run.status, "days": run.days, "processed": run.processed, "error": run.error}


class AssetTriggers(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self, asset_id: str):
        if not (asset := accessible_asset(asset_id, current_user)):
            return {"error": "Asset not found."}, 404
        groups = grouped_triggers(asset_id)
        if component_id := request.args.get("component_id"):
            groups = [group for group in groups if any(t.component_id == component_id for t in group)]
        if search := request.args.get("search", "").strip():
            groups = [group for group in groups if search.casefold() in group[0].phrase.casefold()]
        if request.args.get("enabled") in ("true", "false"):
            groups = [group for group in groups if group[0].enabled == (request.args["enabled"] == "true")]
        total = len(groups)
        pages = max(1, (total + TRIGGERS_PER_PAGE - 1) // TRIGGERS_PER_PAGE)
        page = min(pages, max(1, request.args.get("page", 1, type=int)))
        items = [trigger_response(group[0], group) for group in groups[(page - 1) * TRIGGERS_PER_PAGE : page * TRIGGERS_PER_PAGE]]
        return {"asset_name": asset.name, "items": items, "page": page, "pages": pages, "total": total}, 200

    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        try:
            data = TriggerCreate.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide a component, a phrase up to 200 characters and at most 10 context phrases."}, 400
        component = db.session.scalar(asset_components(asset_id).where(AssetSbomComponent.id == data.component_id))
        if not component:
            return {"error": "Component not found in this asset."}, 404
        product = product_identity(component.inventory)
        triggers = []
        for sibling in db.session.scalars(asset_components(asset_id)):
            if product_identity(sibling.inventory) == product:
                trigger = AssetTrigger(sibling.id, data.phrase, data.context, ["analyst"], enabled=data.enabled)
                trigger.analyst_edited = True
                db.session.add(trigger)
                triggers.append(trigger)
        db.session.commit()
        return trigger_response(triggers[0], triggers), 201


class AssetTriggerEdit(MethodView):
    @auth_required("ASSETS_CREATE")
    def put(self, asset_id: str, trigger_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        group = next((group for group in grouped_triggers(asset_id, lock=True) if any(t.id == trigger_id for t in group)), None)
        if not group:
            return {"error": "Trigger not found."}, 404
        try:
            data = TriggerInput.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Provide a phrase up to 200 characters and at most 10 context phrases."}, 400
        for trigger in group:
            resolve_inheritance_review(trigger)
            trigger.phrase, trigger.context, trigger.enabled = data.phrase, data.context, data.enabled
            trigger.analyst_edited = True
        db.session.execute(db.delete(AssetArticleMatch).where(AssetArticleMatch.trigger_id.in_([t.id for t in group])))
        db.session.commit()
        return trigger_response(group[0], group), 200


class AssetTriggerSelection(MethodView):
    @auth_required("ASSETS_CREATE")
    def post(self, asset_id: str):
        if not accessible_asset(asset_id, current_user):
            return {"error": "Asset not found."}, 404
        try:
            data = TriggerSelection.model_validate(request.get_json(silent=True))
        except ValidationError:
            return {"error": "Select between 1 and 100 triggers and whether to enable them."}, 400
        groups = grouped_triggers(asset_id, lock=True)
        selected = set(data.trigger_ids)
        if not selected.issubset({t.id for group in groups for t in group}):
            return {"error": "A selected trigger does not belong to this asset."}, 404
        triggers = [trigger for group in groups if any(t.id in selected for t in group) for trigger in group]
        for trigger in triggers:
            resolve_inheritance_review(trigger)
            trigger.enabled = data.enabled
            trigger.analyst_edited = True
        if not data.enabled:
            db.session.execute(db.delete(AssetArticleMatch).where(AssetArticleMatch.trigger_id.in_([t.id for t in triggers])))
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
        try:
            filters = IntelligenceFilters.model_validate({**request.args.to_dict(), "asset_id": asset_id})
        except ValidationError:
            return {"error": INTELLIGENCE_FILTER_ERROR}, 400
        data = intelligence_overview(current_user, filters)
        # The individual-asset API exposes each article's evidence directly.
        for story in data["items"]:
            story["articles"] = [article["hosts"][0] for article in story["articles"]]
        return {"asset_name": asset.name, **data}, 200


class AssetsIntelligence(MethodView):
    @auth_required("ASSETS_ACCESS")
    def get(self):
        if "ASSESS_ACCESS" not in current_user.get_permissions():
            return {"error": "Intelligence access is required."}, 403
        try:
            filters = IntelligenceFilters.model_validate(request.args.to_dict())
        except ValidationError:
            return {"error": INTELLIGENCE_FILTER_ERROR}, 400
        return intelligence_overview(current_user, filters), 200


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
        run = start_match_run(asset_id, current_user, data.days)
        if run.status == "FAILED":
            return {"error": run.error}, 503
        return run_response(run), 202


class AssetMatchBatch(MethodView):
    @api_key_required
    def post(self, run_id: str):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"error": "Provide a JSON object."}, 400
        pending = db.session.get(AssetMatchRun, run_id)
        if pending:
            db.session.execute(db.update(Asset).where(Asset.id == pending.asset_id).values(name=Asset.name))
        run = db.session.scalar(db.select(AssetMatchRun).filter_by(id=run_id).with_for_update().execution_options(populate_existing=True))
        if not run:
            return {"error": "Matching run not found."}, 404
        if run.status not in ("COMPLETED", "FAILED", "SUPERSEDED"):
            if data.get("failed") is True:
                run.status, run.error = "FAILED", "The scan could not finish. Please start another scan."
            else:
                scan_batch(run)
            db.session.commit()
        return run_response(run), 200


def initialize(app, base_route: str):
    app.add_url_rule(f"{base_route}/assets/intelligence", view_func=AssetsIntelligence.as_view("assets_intelligence"))
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
