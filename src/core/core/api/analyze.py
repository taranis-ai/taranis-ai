from flask import request, abort
from flask_restx import Resource, Namespace, Api

from core.managers import asset_manager, auth_manager
from core.managers.sse_manager import sse_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model import report_item, report_item_type


class ReportTypes(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self):
        return report_item_type.ReportItemType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class ReportStories(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id):
        return report_item.ReportItem.get_story_ids(report_item_id)

    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id):
        request_data = request.json
        if not isinstance(request_data, list):
            logger.debug("No data in request")
            return "No data in request", 400
        return report_item.ReportItem.set_stories(report_item_id, request_data, auth_manager.get_user_from_jwt())

    @auth_required("ANALYZE_UPDATE")
    def post(self, report_item_id):
        request_data = request.json
        if not isinstance(request_data, list):
            logger.debug("No data in request")
            return "No data in request", 400
        return report_item.ReportItem.add_stories(report_item_id, request_data, auth_manager.get_user_from_jwt())


class ReportItem(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id=None):
        if report_item_id:
            result_json = report_item.ReportItem.get_detail_json(report_item_id)
            return (result_json, 200) if result_json else ("Could not get report item", 404)
        filter_keys = ["search", "completed", "incompleted", "range", "sort", "group"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        filter_args["offset"] = min(int(request.args.get("offset", 0)), (2**31) - 1)
        filter_args["limit"] = min(int(request.args.get("limit", 20)), 200)
        return report_item.ReportItem.get_json(filter_args, auth_manager.get_user_from_jwt())

    @auth_required("ANALYZE_CREATE")
    def post(self):
        try:
            new_report_item, status = report_item.ReportItem.add(request.json, auth_manager.get_user_from_jwt())
        except Exception as ex:
            logger.exception()
            abort(400, f"Error adding report item: {ex}")
        if status == 401:
            abort(401, "Unauthorized")
        if status == 200 and new_report_item:
            asset_manager.report_item_changed(new_report_item)
            sse_manager.report_item_updated({"id": new_report_item.id, "action": "add"})

        return new_report_item.to_detail_dict(), status

    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id):
        request_data = request.json
        if not request_data:
            logger.debug("No data in request")
            return "No data in request", 400
        return report_item.ReportItem.update_report_item(report_item_id, request_data, auth_manager.get_user_from_jwt())

    @auth_required("ANALYZE_DELETE")
    def delete(self, report_item_id):
        result, code = report_item.ReportItem.delete(report_item_id)
        if code == 200:
            sse_manager.report_item_updated({"id": report_item_id, "action": "delete"})
        return result, code


class CloneReportItem(Resource):
    @auth_required("ANALYZE_CREATE")
    def post(self, report_item_id):
        try:
            result, status = report_item.ReportItem.clone(report_item_id, auth_manager.get_user_from_jwt())
        except Exception as ex:
            logger.exception()
            abort(400, f"Error cloning report item: {ex}")
        if status == 200:
            sse_manager.report_item_updated({"id": result["id"], "action": "add"})

        return result, status


class ReportItemLocks(Resource):
    @auth_required("ANALYZE_UPDATE")
    def get(self, report_item_id):
        return sse_manager.to_report_item_json(report_item_id)


class ReportItemLock(Resource):
    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            abort(401, "User not found")
        try:
            return sse_manager.report_item_lock(report_item_id, user.id)
        except Exception as ex:
            logger.exception()
            return str(ex), 500


class ReportItemUnlock(Resource):
    @auth_required("ANALYZE_UPDATE")
    def put(self, report_item_id):
        user = auth_manager.get_user_from_jwt()
        if not user:
            abort(401, "User not found")
        try:
            return sse_manager.report_item_unlock(report_item_id, user.id)
        except Exception as ex:
            logger.exception()
            return str(ex), 500


def initialize(api: Api):
    namespace = Namespace("analyze", description="Analyze API")
    namespace.add_resource(ReportTypes, "/report-types")
    namespace.add_resource(ReportItem, "/report-items/<string:report_item_id>", "/report-items")
    namespace.add_resource(CloneReportItem, "/report-items/<string:report_item_id>/clone")
    namespace.add_resource(ReportStories, "/report-items/<string:report_item_id>/stories")
    namespace.add_resource(ReportItemLocks, "/report-items/<string:report_item_id>/locks")
    namespace.add_resource(
        ReportItemLock,
        "/report-items/<string:report_item_id>/lock",
    )
    namespace.add_resource(
        ReportItemUnlock,
        "/report-items/<string:report_item_id>/unlock",
    )
    api.add_namespace(namespace, path="/analyze")
