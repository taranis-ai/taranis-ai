import io
from flask import request, jsonify, send_file
from flask_restful import Resource

from core.managers import asset_manager, auth_manager, sse_manager
from core.managers.log_manager import logger
from core.managers.auth_manager import auth_required, ACLCheck
from core.model import attribute, report_item, report_item_type


class ReportItemTypes(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self):
        return report_item_type.ReportItemType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class ReportItemGroups(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self):
        return report_item.ReportItem.get_groups()


class ReportItems(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self):
        try:
            filter_keys = ["search", "completed", "incompleted", "range", "sort"]
            filter_args = {k: v for k, v in request.args.items() if k in filter_keys}

            group = request.args.get("group", None)
            if group:
                group = int(group)

            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return report_item.ReportItem.get_json(group, filter_args, offset, limit, auth_manager.get_user_from_jwt())

    @auth_required("ANALYZE_CREATE")
    def post(self):
        new_report_item, status = report_item.ReportItem.add_report_item(request.json, auth_manager.get_user_from_jwt())
        if status == 200:
            asset_manager.report_item_changed(new_report_item)
            sse_manager.remote_access_report_items_updated(new_report_item.report_item_type_id)
            sse_manager.report_items_updated()

        return new_report_item.id, status


class ReportItem(Resource):
    @auth_required("ANALYZE_ACCESS", ACLCheck.REPORT_ITEM_ACCESS)
    def get(self, report_item_id):
        return report_item.ReportItem.get_detail_json(report_item_id)

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id):
        modified, data = report_item.ReportItem.update_report_item(report_item_id, request.json, auth_manager.get_user_from_jwt())
        if modified is True:
            updated_report_item = report_item.ReportItem.find(report_item_id)
            asset_manager.report_item_changed(updated_report_item)
            sse_manager.report_item_updated(data)
            sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

        return data

    @auth_required("ANALYZE_DELETE", ACLCheck.REPORT_ITEM_MODIFY)
    def delete(self, report_item_id):
        result, code = report_item.ReportItem.delete_report_item(report_item_id)
        if code == 200:
            sse_manager.report_items_updated()
        return result, code


class ReportItemData(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id):

        try:
            data = {}
            if "update" in request.args and request.args["update"]:
                data["update"] = request.args["update"]
            if "add" in request.args and request.args["add"]:
                data["add"] = request.args["add"]
            if "title" in request.args and request.args["title"]:
                data["title"] = request.args["title"]
            if "title_prefix" in request.args and request.args["title_prefix"]:
                data["title_prefix"] = request.args["title_prefix"]
            if "completed" in request.args and request.args["completed"]:
                data["completed"] = request.args["completed"]
            if "attribute_id" in request.args and request.args["attribute_id"]:
                data["attribute_id"] = request.args["attribute_id"]
            if "aggregate_ids" in request.args and request.args["aggregate_ids"]:
                data["aggregate_ids"] = request.args["aggregate_ids"].split("--")
            if "remote_report_item_ids" in request.args and request.args["remote_report_item_ids"]:
                data["remote_report_item_ids"] = request.args["remote_report_item_ids"].split("--")
        except Exception:
            logger.log_debug_trace("Error getting Report Item Data")
            return "", 400

        user = auth_manager.get_user_from_jwt()
        if auth_manager.check_acl(report_item_id, ACLCheck.REPORT_ITEM_ACCESS, user) is False:
            return "", 401

        return report_item.ReportItem.get_updated_data(report_item_id, data)


class ReportItemLocks(Resource):
    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def get(self, report_item_id):
        if id in sse_manager.report_item_locks:
            return jsonify(sse_manager.report_item_locks[report_item_id])
        return "{}"


class ReportItemLock(Resource):
    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        sse_manager.report_item_lock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemUnlock(Resource):
    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        sse_manager.report_item_unlock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemHoldLock(Resource):
    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        sse_manager.report_item_hold_lock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemAttributeEnums(Resource):
    @auth_required("ANALYZE_ACCESS")
    def get(self, attribute_id):
        search = request.args.get(key="search", default=None)
        offset = request.args.get(key="offset", default=0)
        limit = request.args.get(key="limit", default=10)
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)


class ReportItemAddAttachment(Resource):
    @auth_required(["ANALYZE_CREATE", "ANALYZE_UPDATE"], ACLCheck.REPORT_ITEM_MODIFY)
    def post(self, report_item_id):
        file = request.files.get("file")
        if not file:
            return {"Error reading file"}

        user = auth_manager.get_user_from_jwt()
        attribute_group_item_id = request.form["attribute_group_item_id"]
        description = request.form["description"]
        data = report_item.ReportItem.add_attachment(report_item_id, attribute_group_item_id, user, file, description)
        updated_report_item = report_item.ReportItem.find(report_item_id)
        asset_manager.report_item_changed(updated_report_item)
        sse_manager.report_item_updated(data)
        sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

        return data


class ReportItemRemoveAttachment(Resource):
    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def delete(self, report_item_id, attribute_id):
        user = auth_manager.get_user_from_jwt()
        data = report_item.ReportItem.remove_attachment(report_item_id, attribute_id, user)
        updated_report_item = report_item.ReportItem.find(report_item_id)
        asset_manager.report_item_changed(updated_report_item)
        sse_manager.report_item_updated(data)
        sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)


class ReportItemDownloadAttachment(Resource):
    def get(self, report_item_id, attribute_id):
        user = auth_manager.get_user_from_jwt()
        if user is not None:
            permissions = user.get_permissions()
            if "ANALYZE_ACCESS" in permissions:
                report_item_attribute = report_item.ReportItemAttribute.find(attribute_id)
                if (
                    report_item_attribute is not None
                    and report_item_attribute.report_item.id == report_item_id
                    and report_item.ReportItem.allowed_with_acl(
                        report_item_attribute.report_item.id,
                        user,
                        False,
                        True,
                        False,
                    )
                ):
                    logger.store_user_activity(
                        user,
                        "ANALYZE_ACCESS",
                        str({"file": report_item_attribute.value}),
                    )

                    return send_file(
                        io.BytesIO(report_item_attribute.binary_data),
                        attachment_filename=report_item_attribute.value,
                        mimetype=report_item_attribute.binary_mime_type,
                        as_attachment=True,
                    )
                else:
                    logger.store_auth_error_activity("Unauthorized access attempt to Report Item Attribute")
            else:
                logger.store_auth_error_activity("Insufficient permissions")
        else:
            logger.store_auth_error_activity("Invalid JWT")


def initialize(api):
    api.add_resource(ReportItemTypes, "/api/v1/analyze/report-item-types")
    api.add_resource(ReportItemGroups, "/api/v1/analyze/report-item-groups")
    api.add_resource(ReportItems, "/api/v1/analyze/report-items")
    api.add_resource(ReportItem, "/api/v1/analyze/report-items/<int:report_item_id>")
    api.add_resource(ReportItemData, "/api/v1/analyze/report-items/<int:report_item_id>/data")
    api.add_resource(ReportItemLocks, "/api/v1/analyze/report-items/<int:report_item_id>/field-locks")
    api.add_resource(
        ReportItemLock,
        "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<int:field_id>/lock",
    )
    api.add_resource(
        ReportItemUnlock,
        "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<int:field_id>/unlock",
    )
    api.add_resource(
        ReportItemHoldLock,
        "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<int:field_id>/hold",
    )
    api.add_resource(
        ReportItemAttributeEnums,
        "/api/v1/analyze/report-item-attributes/<int:attribute_id>/enums",
    )
    api.add_resource(
        ReportItemAddAttachment,
        "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes",
    )
    api.add_resource(
        ReportItemRemoveAttachment,
        "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes/<int:attribute_id>",
    )
    api.add_resource(
        ReportItemDownloadAttachment,
        "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes/<int:attribute_id>/file",
    )
