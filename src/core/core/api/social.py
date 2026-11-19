from flask import Blueprint, Flask, Response, request
from flask_jwt_extended import current_user
from models.base import TaranisBaseModel
from models.social import AttachPosts, BeatFilters, CollectedImage, Contribution, FigureSelection, SaveBeat
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.config import Config
from core.managers.auth_manager import api_key_required, auth_required
from core.managers.db_manager import db
from core.managers.realtime_publisher import realtime_publisher
from core.model.osint_source import OSINTSource
from core.model.report_item import ReportItem
from core.model.social import SocialBeat, SocialImage, SocialPost
from core.service import social
from core.service.cache_invalidation import SCOPE_PUBLISH_VIEWS, SCOPE_STORY_REPORT_VIEWS, invalidate_frontend_cache_on_success


bp = Blueprint("social", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api")


@bp.errorhandler(ValidationError)
def invalid(error):
    db.session.rollback()
    return TaranisBaseModel.validation_error_response(error, "Invalid social monitor input"), 400


@bp.errorhandler(IntegrityError)
def conflict(_error):
    db.session.rollback()
    return {"error": "The selection changed. Refresh and retry."}, 409


@bp.route("/worker/social/<source_id>", methods=["GET", "POST"])
@api_key_required
def collect(source_id):
    source = db.session.scalar(select(OSINTSource).filter_by(id=source_id).with_for_update())
    if not source or source.type not in social.SOCIAL_TYPES:
        return {"error": "Social source unavailable"}, 404
    if request.method == "GET":
        return {"keys": social.due_keys(source)}
    payload = request.get_json()
    if isinstance(payload, dict) and isinstance(payload.get("removed"), str):
        post = db.session.scalar(select(SocialPost).filter_by(source_id=source.id, key=payload["removed"]))
        if post:
            social.withdraw_images([i.id for i in post.images])
            db.session.delete(post)
            db.session.commit()
        invalidate_frontend_cache_on_success(200, scopes=(SCOPE_PUBLISH_VIEWS,))
        return {"message": "Contribution removed"}
    data = Contribution.model_validate(payload)
    try:
        return social.ingest(source, data)
    except ValueError:
        db.session.rollback()
        return {"error": "Invalid social contribution"}, 400


@bp.post("/worker/social/<source_id>/<post_id>/image")
@api_key_required
def upload_image(source_id, post_id):
    data = CollectedImage.model_validate(request.get_json())
    post = db.session.scalar(select(SocialPost).filter_by(id=post_id, source_id=source_id).with_for_update())
    if not post or not (asset := next((i for i in post.images if i.key == data.key), None)):
        return {"error": "Image no longer belongs to this contribution"}, 409
    try:
        social.store_image(asset, data)
    except ValueError:
        db.session.rollback()
        return {"error": "Invalid image data"}, 400
    db.session.commit()
    return {"id": asset.id}


@bp.get("/assess/social")
@auth_required("ASSESS_ACCESS")
def monitor():
    sources = social.visible_sources(current_user)
    filters = BeatFilters.model_validate(
        {
            "sources": request.args.getlist("sources"),
            "platform": request.args.get("platform") or None,
            "search": request.args.get("search", ""),
            "images": request.args.get("images", False),
        }
    )
    page = max(0, min(request.args.get("page", 0, type=int), 1000000))
    result = social.feed(current_user, sources, filters, page)
    statuses = []
    for source in sources.values():
        status = source.status or {}
        statuses.append({"id": source.id, "name": source.name, "status": status.get("status"), "last_success": status.get("last_success")})
    beats = db.session.scalars(select(SocialBeat).filter_by(user_id=current_user.id).order_by(SocialBeat.name))
    return {**result, "sources": statuses, "beats": [{"name": b.name, "filters": b.filters} for b in beats], "page": page}


@bp.post("/assess/social/beats")
@auth_required("ASSESS_ACCESS")
def save_beat():
    data = SaveBeat.model_validate(request.get_json())
    if set(data.sources) - social.visible_sources(current_user).keys():
        return {"error": "Selected source unavailable"}, 404
    name = data.name.strip()
    beat = db.session.scalar(select(SocialBeat).filter_by(user_id=current_user.id, name=name))
    if not beat:
        beat = SocialBeat(user_id=current_user.id, name=name)
        db.session.add(beat)
    beat.filters = data.model_dump(exclude={"name"}, exclude_none=True)
    db.session.commit()
    return {"id": beat.id}


@bp.get("/assess/social/posts/<post_id>")
@auth_required("ASSESS_ACCESS")
def thread(post_id):
    post = SocialPost.get(post_id)
    if not post or post.source_id not in social.visible_sources(current_user):
        return {"error": "Contribution unavailable"}, 404
    return social.thread_view(post, current_user, max(0, min(request.args.get("page", 0, type=int), 1000000)))


@bp.get("/assess/social/material/<item_id>")
@auth_required("ASSESS_ACCESS")
def material(item_id):
    post = db.session.scalar(select(SocialPost).filter_by(item_id=item_id))
    if (
        not post
        or post.source_id not in social.visible_sources(current_user)
        or not post.item
        or not post.item.story
        or not post.item.story.allowed_to_read(current_user)
    ):
        return {"error": "Source contribution unavailable"}, 404
    return social.post_view(post, current_user)


@bp.get("/assess/social/images/<image_id>")
@auth_required("ASSESS_ACCESS")
def image(image_id):
    asset = SocialImage.get(image_id)
    if not asset or not asset.mime or asset.post.source_id not in social.visible_sources(current_user):
        return {"error": "Image unavailable"}, 404
    thumb = request.args.get("size") == "thumbnail"
    return Response(
        asset.thumbnail if thumb else asset.original,
        mimetype="image/jpeg" if thumb else asset.mime,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Content-Disposition": "inline"},
    )


@bp.post("/assess/social/attach")
@auth_required("ASSESS_ACCESS")
def attach():
    result, status = social.attach(AttachPosts.model_validate(request.get_json()), current_user)
    if status == 200:
        invalidate_frontend_cache_on_success(status, scopes=(SCOPE_STORY_REPORT_VIEWS,))
        realtime_publisher.assess_changed()
    return result, status


@bp.route("/analyze/reports/<report_id>/figures", methods=["GET", "PUT"])
@auth_required("ANALYZE_ACCESS")
def report_figures(report_id):
    report = db.session.scalar(select(ReportItem).filter_by(id=report_id).with_for_update())
    if not report or "ASSESS_ACCESS" not in current_user.get_permissions() or not report.access_allowed(current_user):
        return {"error": "Report unavailable"}, 404
    if request.method == "PUT":
        if "ANALYZE_UPDATE" not in current_user.get_permissions() or not report.access_allowed(current_user, require_write_access=True):
            return {"error": "Report is read-only"}, 403
        result, status = social.save_figures(report, FigureSelection.model_validate(request.get_json()), current_user)
        invalidate_frontend_cache_on_success(status, scopes=(SCOPE_STORY_REPORT_VIEWS,))
        return result, status
    selected = {f.image_id: f for f in social.figures(report)}
    rows = []
    for asset in social.report_images(report, current_user):
        figure = selected.get(asset.id)
        rows.append(
            {
                "id": asset.id,
                "author": asset.post.author,
                "platform": asset.post.platform,
                "warning": asset.post.warning,
                "url": asset.post.url,
                "eligible": social.eligible(asset),
                "available": bool(asset.mime),
                "caption": figure.caption if figure else "",
                "alt": figure.alt if figure else asset.alt,
                "position": figure.position + 1 if figure else None,
            }
        )
    return {"images": sorted(rows, key=lambda row: row["position"] or len(rows) + 1)}


def initialize(app: Flask):
    app.register_blueprint(bp)
