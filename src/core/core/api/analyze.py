from flask import Blueprint, request, abort, Flask
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.managers import asset_manager
from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model import report_item, report_item_type
from core.model.revision import ReportRevision
from core.config import Config


class ReportTypes(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self):
        return report_item_type.ReportItemType.get_all_for_api(filter_args=None, with_count=False, user=current_user)


class ReportStories(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id: str):
        return report_item.ReportItem.get_story_ids(report_item_id)

    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id: str):
        request_data = request.json
        if not isinstance(request_data, list):
            logger.warning("No data in request")
            return {"error": "No data in request"}, 400
        return report_item.ReportItem.set_stories(report_item_id, request_data, current_user)

    @auth_required("ANALYZE_UPDATE")
    def post(self, report_item_id: str):
        request_data = request.json
        if not isinstance(request_data, list):
            logger.warning("No data in request")
            return {"error": "No data in request"}, 400
        return report_item.ReportItem.add_stories(report_item_id, request_data, current_user)


class ReportItem(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id: str | None = None):
        if report_item_id:
            return report_item.ReportItem.get_for_api(report_item_id)
        filter_keys = ["search", "completed", "range", "sort", "group"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        filter_args["offset"] = min(int(request.args.get("offset", 0)), (2**31) - 1)
        filter_args["limit"] = min(int(request.args.get("limit", 20)), 200)
        return report_item.ReportItem.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("ANALYZE_CREATE")
    def post(self):
        try:
            if not request.json:
                logger.debug("No data in request")
                return {"error": "No data in request"}, 400
            new_report_item, status = report_item.ReportItem.add(request.json, current_user)
            if status != 200:
                return new_report_item, status
        except Exception as ex:
            logger.exception()
            return abort(400, f"Error adding report item: {ex}")
        if status == 401:
            return abort(401, "Unauthorized")
        if status == 200 and new_report_item:
            asset_manager.report_item_changed(new_report_item)
            sse_manager.report_item_updated(new_report_item.id)

        return {"message": "New report item created", "id": new_report_item.id, "report": new_report_item.to_detail_dict()}, status

    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id: str):
        request_data = request.json
        if not request_data:
            logger.debug("No data in request")
            return {"error": "No data in request"}, 400
        updated_report, status = report_item.ReportItem.update_report_item(report_item_id, request_data, current_user)
        if status == 200:
            sse_manager.report_item_updated(report_item_id)
        return {"message": "Report item updated", "id": report_item_id, "report": updated_report}, status

    @auth_required("ANALYZE_DELETE")
    def delete(self, report_item_id: str):
        result, code = report_item.ReportItem.delete(report_item_id)
        if code == 200:
            sse_manager.report_item_updated(report_item_id)
        return result, code


class CloneReportItem(MethodView):
    @auth_required("ANALYZE_CREATE")
    def post(self, report_item_id: str):
        try:
            result, status = report_item.ReportItem.clone(report_item_id, current_user)
        except Exception as ex:
            logger.exception()
            return abort(400, f"Error cloning report item: {ex}")
        if status == 200:
            sse_manager.report_item_updated(result["id"])

        return result, status


class ReportItemLocks(MethodView):
    @auth_required("ANALYZE_UPDATE")
    def get(self, report_item_id: str):
        return sse_manager.to_report_item_json(report_item_id)


class ReportItemLock(MethodView):
    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id: str):
        user = current_user
        if not user:
            return abort(401, "User not found")
        try:
            return sse_manager.report_item_lock(report_item_id, user.id)
        except Exception as ex:
            logger.exception()
            return str(ex), 500

    @auth_required("ANALYZE_UPDATE")
    def delete(self, report_item_id: str):
        user = current_user
        if not user:
            return abort(401, "User not found")
        try:
            return sse_manager.report_item_unlock(report_item_id, user.id)
        except Exception as ex:
            logger.exception()
            return str(ex), 500


class ReportItemRevisions(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id: str):
        """Get all revisions for a report item"""
        from core.managers.db_manager import db
        
        revisions = db.session.execute(
            db.select(ReportRevision)
            .filter(ReportRevision.report_item_id == report_item_id)
            .order_by(ReportRevision.revision.desc())
        ).scalars().all()
        
        return {
            "total_count": len(revisions),
            "items": [
                {
                    "id": rev.id,
                    "revision": rev.revision,
                    "created_at": rev.created_at.isoformat() if rev.created_at else None,
                    "created_by": rev.created_by.username if rev.created_by else None,
                    "created_by_id": rev.created_by_id,
                    "note": rev.note,
                }
                for rev in revisions
            ]
        }, 200


class ReportItemRevisionData(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id: str, revision_number: int):
        """Get data for a specific revision"""
        from core.managers.db_manager import db
        
        revision = db.session.execute(
            db.select(ReportRevision)
            .filter(ReportRevision.report_item_id == report_item_id)
            .filter(ReportRevision.revision == revision_number)
        ).scalar_one_or_none()
        
        if not revision:
            return {"error": "Revision not found"}, 404
            
        return {
            "id": revision.id,
            "revision": revision.revision,
            "created_at": revision.created_at.isoformat() if revision.created_at else None,
            "created_by": revision.created_by.username if revision.created_by else None,
            "created_by_id": revision.created_by_id,
            "note": revision.note,
            "data": revision.data,
        }, 200


def initialize(app: Flask):
    analyze_bp = Blueprint("analyze", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/analyze")

    analyze_bp.add_url_rule("/report-types", view_func=ReportTypes.as_view("report_types"))
    analyze_bp.add_url_rule("/report-items", view_func=ReportItem.as_view("report_items"))
    analyze_bp.add_url_rule("/reports", view_func=ReportItem.as_view("reports"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>", view_func=ReportItem.as_view("report_item"))
    analyze_bp.add_url_rule("/report/<string:report_item_id>", view_func=ReportItem.as_view("report"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>/clone", view_func=CloneReportItem.as_view("clone_report_item"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>/stories", view_func=ReportStories.as_view("report_stories"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>/locks", view_func=ReportItemLocks.as_view("report_item_locks"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>/lock", view_func=ReportItemLock.as_view("report_item_lock"))
    analyze_bp.add_url_rule("/report-items/<string:report_item_id>/revisions", view_func=ReportItemRevisions.as_view("report_item_revisions"))
    analyze_bp.add_url_rule(
        "/report-items/<string:report_item_id>/revisions/<int:revision_number>",
        view_func=ReportItemRevisionData.as_view("report_item_revision_data"),
    )

    app.register_blueprint(analyze_bp)
