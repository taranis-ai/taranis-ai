import base64
import io
from typing import Any

from flask import Blueprint, Flask, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.admin import OSINTSource as OSINTSourceModel
from psycopg.errors import NotNullViolation, UniqueViolation  # noqa: F401
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError  # noqa: F401

from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.managers.data_manager import (
    delete_template,
    validate_presenter_template_id,
)
from core.managers.decorators import extract_args
from core.model import (
    attribute,
    bot,
    connector,
    organization,
    osint_source,
    product_type,
    publisher_preset,
    report_item_type,
    role,
    role_based_access,
    task,
    user,
    word_list,
    worker,
)
from core.model.permission import Permission
from core.service.cache_invalidation import cache_invalidation_service
from core.service.template_service import build_template_response, build_templates_list, create_or_update_template, validate_template_content


def convert_integrity_error(error: IntegrityError) -> str:
    """
    Converts an IntegrityError into a more descriptive ValidationError.
    Currently handles UniqueViolation and NotNullViolation errors using psycopg2's diagnostics.
    """
    orig = error.orig
    if isinstance(orig, UniqueViolation):
        constraint = orig.diag.constraint_name
        field = constraint.rsplit("_", 2)[-2] if constraint else None
        if field:
            return f"A record with this field: '{field}' already exists."
    if isinstance(orig, NotNullViolation):
        column = getattr(orig.diag, "column_name", None)
        table = getattr(orig.diag, "table_name", None)
        if column and table:
            pretty_column = column.replace("_", " ")
            pretty_table = table.replace("_", " ")
            return f"Cannot set {pretty_column} to null because {pretty_table} still requires a value."
        if column:
            pretty_column = column.replace("_", " ")
            return f"A value for {pretty_column} is required."
        return "A required value is missing."
    return str(error)


def _invalidate_admin_cache(status_code: int) -> int:
    if 200 <= status_code < 300:
        return cache_invalidation_service.invalidate_all()
    return 0


class DictionariesReload(MethodView):
    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def post(self, dictionary_type: str):
        attribute.Attribute.load_dictionaries(dictionary_type)
        return {"message": "success"}, 200


class ACLEntries(MethodView):
    @auth_required("CONFIG_ACL_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, acl_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if acl_id:
            return role_based_access.RoleBasedAccess.get_for_api(acl_id)
        return role_based_access.RoleBasedAccess.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self):
        acl = role_based_access.RoleBasedAccess.add(request.json)
        _invalidate_admin_cache(201)
        return {"message": "ACL created", "id": acl.id}, 201

    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id: int | None = None):
        if acl_id is None:
            return {"error": "No acl_id provided"}, 400
        response, status = role_based_access.RoleBasedAccess.update(acl_id, request.json)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id: int | None = None):
        if acl_id is None:
            return {"error": "No acl_id provided"}, 400
        response, status = role_based_access.RoleBasedAccess.delete(acl_id)
        _invalidate_admin_cache(status)
        return response, status


class Attributes(MethodView):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS"])
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, attribute_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if attribute_id:
            return attribute.Attribute.get_for_api(attribute_id)

        return attribute.Attribute.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self):
        attribute_result = attribute.Attribute.add(request.json)
        _invalidate_admin_cache(201)
        return {"message": "Attribute added", "id": attribute_result.id}, 201

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id: int | None = None):
        if attribute_id is None:
            return {"error": "No attribute_id provided"}, 400
        response, status = attribute.Attribute.update(attribute_id, request.json)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id: int | None = None):
        if attribute_id is None:
            return {"error": "No attribute_id provided"}, 400
        response, status = attribute.Attribute.delete(attribute_id)
        _invalidate_admin_cache(status)
        return response, status


class ReportItemTypesImport(MethodView):
    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self):
        return {"error": "Not implemented"}, 400
        # if file := request.files.get("file"):
        #     if rts := report_item_type.ReportItemType.import_report_types(file):
        #         return {"report_types": [rt.id for rt in rts], "count": len(rts), "message": "Successfully imported report types"}
        #     return {"error": "Unable to import"}, 400
        # return {"error": "No file provided"}, 400


class ReportItemTypesExport(MethodView):
    @auth_required("CONFIG_REPORT_TYPE_ACCESS")
    def get(self):
        source_ids = request.args.getlist("ids")
        data = report_item_type.ReportItemType.export(source_ids)
        if data is None:
            return {"error": "Unable to export"}, 400
        return send_file(
            io.BytesIO(data),
            download_name="report_types_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class ReportItemTypes(MethodView):
    @auth_required("CONFIG_REPORT_TYPE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, type_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if type_id:
            return report_item_type.ReportItemType.get_for_api(type_id)
        return report_item_type.ReportItemType.get_all_for_api(filter_args, True, current_user)

    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self):
        try:
            item = report_item_type.ReportItemType.add(request.json)
            _invalidate_admin_cache(201)
            return {"message": f"ReportItemType {item.title} added", "id": item.id}, 201
        except Exception:
            logger.exception("Failed to add report item type")
            return {"error": "Failed to add report item type"}, 500

    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id: int | None = None):
        if type_id is None:
            return {"error": "No type_id provided"}, 400
        if item := report_item_type.ReportItemType.update(type_id, request.json):
            _invalidate_admin_cache(200)
            return {"message": f"Report item type {item.title} updated", "id": f"{item.id}"}, 200
        return {"error": f"Report item type with ID: {type_id} not found"}, 404

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id: int | None = None):
        if type_id is None:
            return {"error": "No type_id provided"}, 400
        response, status = report_item_type.ReportItemType.delete(type_id)
        _invalidate_admin_cache(status)
        return response, status


class ProductTypes(MethodView):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, type_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if type_id:
            return product_type.ProductType.get_for_api(type_id)
        return product_type.ProductType.get_all_for_api(filter_args, True, current_user)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        try:
            product = product_type.ProductType.add(request.json)
            _invalidate_admin_cache(201)
            return {"message": "Product type created", "id": product.id}, 201
        except ValueError as e:
            return {"error": str(e)}, 400
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception as e:
            logger.error(f"Error creating product type: {e}")
            return {"error": "Failed to create product type"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id: int | None = None):
        if type_id is None:
            return {"error": "No type_id provided"}, 400
        try:
            response, status = product_type.ProductType.update(type_id, request.json, current_user)
            _invalidate_admin_cache(status)
            return response, status
        except ValueError as e:
            return {"error": str(e)}, 400
        except Exception as e:
            logger.error(f"Error updating product type: {e}")
            return {"error": "Failed to update product type"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id: int | None = None):
        if type_id is None:
            return {"error": "No type_id provided"}, 400
        try:
            response, status = product_type.ProductType.delete(type_id)
            _invalidate_admin_cache(status)
            return response, status
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception as e:
            logger.error(f"Error deleting product type: {e}")
            return {"error": "Failed to delete product type"}, 500


class Parameters(MethodView):
    @auth_required("CONFIG_ACCESS")
    def get(self):
        return worker.Worker.get_parameter_map(), 200


class WorkerParameters(MethodView):
    @auth_required("CONFIG_ACCESS")
    def get(self):
        x = worker.Worker.get_parameter_map()
        result = [{"id": key, "parameters": value} for key, value in x.items()]
        return {"items": result}, 200


class Permissions(MethodView):
    @auth_required("CONFIG_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, filter_args: dict[str, Any] | None = None):
        return Permission.get_all_for_api(filter_args, True)


class Roles(MethodView):
    @auth_required("CONFIG_ROLE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, role_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if role_id:
            return role.Role.get_for_api(role_id)
        return role.Role.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        new_role = role.Role.add(request.json)
        _invalidate_admin_cache(201)
        return {"message": "Role created", "id": new_role.id}, 201

    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id: int | None = None):
        if role_id is None:
            return {"error": "No role_id provided"}, 400
        if data := request.json:
            response, status = role.Role.update(role_id, data)
            _invalidate_admin_cache(status)
            return response, status
        return {"error": "No data provided"}, 400

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id: int | None = None):
        if role_id is None:
            return {"error": "No role_id provided"}, 400
        if user.UserRole.has_assigned_user(role_id):
            logger.warning(f"Role {role_id} cannot be deleted, it has assigned users")
            return {"error": f"Role {role_id} cannot be deleted, it has assigned users"}, 400
        response, status = role.Role.delete(role_id)
        _invalidate_admin_cache(status)
        return response, status


class Templates(MethodView):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self, template_path: str | None = None):
        if template_path:
            resp = build_template_response(template_path)
            return jsonify(resp), 200

        # List all templates
        items = build_templates_list()
        return jsonify({"items": items, "total_count": len(items)}), 200

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self, template_path: str | None = None):
        # Use shared logic for create/update
        if not request.json:
            return {"error": "No data provided"}, 400
        template_id = request.json.get("id")
        base64_content = request.json.get("content")
        response, status = create_or_update_template(template_id, base64_content)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def put(self, template_path: str | None = None):
        if not template_path:
            return {"error": "No template_path provided"}, 400
        # Use shared logic for create/update
        if not request.json:
            return {"error": "No data provided"}, 400
        base64_content = request.json.get("content")
        response, status = create_or_update_template(template_path, base64_content)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, template_path: str | None = None):
        if not template_path:
            return {"error": "No template_path provided"}, 400
        try:
            validate_presenter_template_id(template_path)
        except ValueError as e:
            return {"error": str(e)}, 400
        if delete_template(template_path):
            _invalidate_admin_cache(200)
            return {"message": "Template deleted", "path": template_path}, 200
        return {"error": "Could not delete template"}, 500


class TemplateValidation(MethodView):
    """Endpoint for validating Jinja2 templates without saving them."""

    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def post(self):
        """Validate a Jinja2 template without saving it."""
        if not request.json:
            return {"error": "No data provided"}, 400

        template_content = request.json.get("content")
        if not template_content:
            return {"error": "No template content provided"}, 400

        try:
            # Decode base64 content if needed
            if request.json.get("is_base64", False):
                template_content = base64.b64decode(template_content).decode("utf-8")

            validation_result = validate_template_content(template_content)
            return {
                "is_valid": validation_result["is_valid"],
                "error_message": validation_result.get("error_message", ""),
                "error_type": validation_result.get("error_type", ""),
                "message": "Template is valid" if validation_result["is_valid"] else "Template has validation errors",
            }, 200

        except Exception as e:
            logger.error(f"Error validating template: {e}")
            return {"error": f"Validation failed: {str(e)}"}, 500


class Organizations(MethodView):
    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, organization_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if organization_id:
            return organization.Organization.get_for_api(organization_id)
        return organization.Organization.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self):
        org = organization.Organization.add(request.json)
        _invalidate_admin_cache(201)
        return {"message": "Organization created", "id": org.id}, 201

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id: int | None = None):
        if organization_id is None:
            return {"error": "No organization_id provided"}, 400
        response, status = organization.Organization.update(organization_id, request.json)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id: int | None = None):
        if organization_id is None:
            return {"error": "No organization_id provided"}, 400
        response, status = organization.Organization.delete(organization_id)
        _invalidate_admin_cache(status)
        return response, status


class UsersImport(MethodView):
    @auth_required("CONFIG_USER_UPDATE")
    def post(self):
        user_list = request.json
        if not isinstance(user_list, list):
            return {"error": "Invalid data format"}, 400
        if users := user.User.import_users(user_list):
            _invalidate_admin_cache(200)
            return {"users": users, "count": len(users), "message": "Successfully imported users"}
        return {"error": "Unable to import"}, 400


class UsersExport(MethodView):
    @auth_required("CONFIG_USER_ACCESS")
    def get(self):
        user_ids = request.args.getlist("ids")
        data = user.User.export(user_ids)
        if data is None:
            return {"error": "Unable to export"}, 400
        return send_file(
            io.BytesIO(data),
            download_name="users_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class Users(MethodView):
    @auth_required("CONFIG_USER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, user_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if user_id:
            return user.User.get_for_api(user_id)
        return user.User.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_USER_CREATE")
    def post(self):
        try:
            new_user = user.User.add(request.json)
            _invalidate_admin_cache(201)
            return {"message": f"User {new_user.username} created", "id": new_user.id}, 201
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception()
            return {"error": "Could not create user"}, 400

    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id: int | None = None):
        if user_id is None:
            return {"error": "No user_id provided"}, 400
        try:
            response, status = user.User.update(user_id, request.json)
            _invalidate_admin_cache(status)
            return response, status
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception()
            return {"error": "Could not update user"}, 400

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id: int | None = None):
        if user_id is None:
            return {"error": "No user_id provided"}, 400
        try:
            response, status = user.User.delete(user_id)
            _invalidate_admin_cache(status)
            return response, status
        except Exception:
            logger.exception()
            return {"error": "Could not delete user"}, 400


class Bots(MethodView):
    @auth_required("CONFIG_BOT_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, bot_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if bot_id:
            return bot.Bot.get_for_api(bot_id)
        return bot.Bot.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_BOT_UPDATE")
    def put(self, bot_id: str | None = None):
        if bot_id is None:
            return {"error": "No bot_id provided"}, 400
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if updated_bot := bot.Bot.update(bot_id, update_data):
                logger.debug(f"Successfully updated {updated_bot}")
                _invalidate_admin_cache(200)
                return {"message": f"Successfully upated {updated_bot.name}", "id": f"{updated_bot.id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 400
        return {"error": f"Bot with ID: {bot_id} not found"}, 404

    @auth_required("CONFIG_BOT_CREATE")
    def post(self):
        new_bot = bot.Bot.add(request.json)
        _invalidate_admin_cache(201)
        return {"message": f"Bot {new_bot.name} created", "id": new_bot.id}, 201

    @auth_required("CONFIG_BOT_DELETE")
    def delete(self, bot_id: str | None = None):
        if bot_id is None:
            return {"error": "No bot_id provided"}, 400
        response, status = bot.Bot.delete(bot_id)
        _invalidate_admin_cache(status)
        return response, status


class BotExecute(MethodView):
    @auth_required("BOT_EXECUTE")
    def post(self, bot_id: str):
        return queue_manager.queue_manager.execute_bot_task(bot_id)


class QueueStatus(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_queue_status()


class QueueTasks(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_queued_tasks()


class ActiveJobs(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_active_jobs()


class FailedJobs(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_failed_jobs()


class WorkerStats(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_worker_stats()


class SchedulerDashboard(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        scheduled_jobs, scheduled_status = queue_manager.queue_manager.get_scheduled_jobs()
        if scheduled_status != 200:
            return scheduled_jobs, scheduled_status

        queues, queue_status = queue_manager.queue_manager.get_queued_tasks()
        if queue_status != 200:
            return queues, queue_status

        worker_stats, worker_stats_status = queue_manager.queue_manager.get_worker_stats()
        if worker_stats_status != 200:
            return worker_stats, worker_stats_status

        active_jobs, active_status = queue_manager.queue_manager.get_active_jobs()
        if active_status != 200:
            return active_jobs, active_status

        failed_jobs, failed_status = queue_manager.queue_manager.get_failed_jobs()
        if failed_status != 200:
            return failed_jobs, failed_status

        return {
            "scheduled_jobs": scheduled_jobs.get("items", []),
            "scheduled_total_count": scheduled_jobs.get("total_count", 0),
            "queues": queues if isinstance(queues, list) else [],
            "worker_stats": worker_stats if isinstance(worker_stats, dict) else {},
            "active_jobs": active_jobs.get("items", []),
            "active_total_count": active_jobs.get("total_count", 0),
            "failed_jobs": failed_jobs.get("items", []),
            "failed_total_count": failed_jobs.get("total_count", 0),
        }, 200


class CronJobs(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_cron_job_configs()


class Schedule(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self, task_id: str | None = None):
        try:
            if task_id:
                return queue_manager.queue_manager.get_scheduled_job(task_id)

            return queue_manager.queue_manager.get_scheduled_jobs()
        except Exception:
            logger.exception()
            return {"error": "Failed to get schedules"}, 500


class Connectors(MethodView):
    @auth_required("CONFIG_CONNECTOR_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, connector_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if connector_id:
            return connector.Connector.get_for_api(connector_id)
        return connector.Connector.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_CONNECTOR_CREATE")
    def post(self):
        if source := connector.Connector.add(request.json):
            _invalidate_admin_cache(201)
            return {"id": source.id, "message": "Connector created successfully"}, 201
        return {"error": "Connector could not be created"}, 400

    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def put(self, connector_id: str | None = None):
        if connector_id is None:
            return {"error": "No connector_id provided"}, 400
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if source := connector.Connector.update(connector_id, update_data):
                _invalidate_admin_cache(200)
                return {"message": f"Connector {source.name} updated", "id": f"{connector_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 500
        return {"error": f"Connector with ID: {connector_id} not found"}, 404

    @auth_required("CONFIG_CONNECTOR_DELETE")
    def delete(self, connector_id: str | None = None):
        if connector_id is None:
            return {"error": "No connector_id provided"}, 400
        # TODO: Implement force delete logic if needed
        response, status = connector.Connector.delete(connector_id)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def patch(self, connector_id: str | None = None):
        if connector_id is None:
            return {"error": "No connector_id provided"}, 400
        if not request.json:
            return {"error": "No data provided"}, 400
        if state := request.json.get("state"):
            update_data = {"state": state}
        else:
            update_data = request.json
        try:
            if source := connector.Connector.update(connector_id, update_data):
                _invalidate_admin_cache(200)
                return {"message": f"Connector {source.name} updated", "id": f"{connector_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 400
        return {"error": f"Connector with ID: {connector_id} not found"}, 404


class ConnectorsPull(MethodView):
    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def post(self, connector_id: str):
        """Trigger collection of stories from the external system."""
        try:
            collected_stories = queue_manager.queue_manager.pull_from_connector(connector_id=connector_id)

            return {"message": "Stories successfully collected.", "data": collected_stories}, 200
        except Exception as e:
            return {"error": str(e)}, 500


class OSINTSources(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "type", "fetch_all")
    def get(self, source_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if source_id:
            return osint_source.OSINTSource.get_for_api(source_id)
        return osint_source.OSINTSource.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        try:
            if source := osint_source.OSINTSource.add(request.json):
                _invalidate_admin_cache(201)
                return {"id": source.id, "message": "OSINT source created successfully"}, 201
        except ValidationError as exc:
            return {"error": OSINTSourceModel.format_validation_errors(exc)}, 400
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return {"error": "OSINT source could not be created"}, 400

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id: str | None = None):
        if source_id is None:
            return {"error": "No source_id provided"}, 400
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if source := osint_source.OSINTSource.update(source_id, update_data):
                _invalidate_admin_cache(200)
                return {"message": f"OSINT Source {source.name} updated", "id": f"{source_id}"}, 200
        except ValidationError as exc:
            return {"error": OSINTSourceModel.format_validation_errors(exc)}, 400
        except ValueError as e:
            return {"error": str(e)}, 400
        return {"error": f"OSINT Source with ID: {source_id} not found"}, 404

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id: str | None = None):
        if source_id is None:
            return {"error": "No source_id provided"}, 400
        force = request.args.get("force", default=False, type=bool)
        if not force:
            from core.service.news_item import NewsItemService as _NewsItemService

            if _NewsItemService.has_related_news_items(source_id):
                return {
                    "error": f"""OSINT Source with ID: {source_id} has related News Items.
                To delete this item and all related News Items, set the 'force' flag."""
                }, 409

        response, status = osint_source.OSINTSource.delete(source_id, force=force)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def patch(self, source_id: str | None = None):
        if source_id is None:
            return {"error": "No source_id provided"}, 400
        if request.json:
            state = request.json.get("state")
        else:
            state = request.args.get("state", default="enabled", type=str)
        logger.debug(f"Toggling OSINT source {source_id} to state {state}")
        response, status = osint_source.OSINTSource.toggle_state(source_id, state)
        _invalidate_admin_cache(status)
        return response, status


class OSINTSourceCollect(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def post(self, source_id: str | None = None):
        if source_id:
            if source := osint_source.OSINTSource.get(source_id):
                return queue_manager.queue_manager.collect_osint_source(source_id, task_id=source.task_id)
            return {"error": f"OSINT Source with ID: {source_id} not found"}, 404
        return queue_manager.queue_manager.collect_all_osint_sources()


class OSINTSourcePreview(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def get(self, source_id: str):
        task_id = f"source_preview_{source_id}"

        if result := task.Task.get(task_id):
            return result.to_dict(), 200
        return queue_manager.queue_manager.preview_osint_source(source_id)

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def post(self, source_id: str):
        return queue_manager.queue_manager.preview_osint_source(source_id)


class OSINTSourcesExport(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        source_ids = request.args.getlist("ids")
        with_groups = request.args.get("groups", default=False, type=bool)
        with_secrets = request.args.get("secrets", default=False, type=bool)
        export_args = {"source_ids": source_ids, "with_groups": with_groups, "with_secrets": with_secrets}
        data = osint_source.OSINTSource.export_osint_sources(export_args)
        if data is None:
            return {"error": "Unable to export"}, 400
        return send_file(
            io.BytesIO(data),
            download_name="osint_sources_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class OSINTSourcesImport(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        try:
            sources = None
            if file := request.files.get("file"):
                sources = osint_source.OSINTSource.import_osint_sources(file)
            if json_data := request.get_json(silent=True):
                sources = osint_source.OSINTSource.import_osint_sources_from_json(json_data)
        except ValidationError as exc:
            return {"error": OSINTSourceModel.format_validation_errors(exc)}, 400
        if sources is None:
            logger.error("Failed to import OSINT sources")
            return {"error": "Unable to import"}, 400
        _invalidate_admin_cache(200)
        return {"sources": sources, "count": len(sources), "message": "Successfully imported sources"}


class OSINTSourceGroups(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, group_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if group_id:
            return osint_source.OSINTSourceGroup.get_for_api(group_id)
        return osint_source.OSINTSourceGroup.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        source_group = osint_source.OSINTSourceGroup.add(request.json)
        _invalidate_admin_cache(200)
        return {"id": source_group.id, "message": "OSINT source group created successfully"}, 200

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id: str | None = None):
        if group_id is None:
            return {"error": "No group_id provided"}, 400
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        response, status = osint_source.OSINTSourceGroup.update(group_id, data, user=current_user)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id: str | None = None):
        if group_id is None:
            return {"error": "No group_id provided"}, 400
        response, status = osint_source.OSINTSourceGroup.delete(group_id)
        _invalidate_admin_cache(status)
        return response, status


class Presenters(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, filter_args: dict[str, Any] | None = None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class Publishers(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, filter_args: dict[str, Any] | None = None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class PublisherPresets(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, preset_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if preset_id:
            return publisher_preset.PublisherPreset.get_for_api(preset_id)
        return publisher_preset.PublisherPreset.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_PUBLISHER_CREATE")
    def post(self):
        pub_result = publisher_preset.PublisherPreset.add(request.json)
        _invalidate_admin_cache(200)
        return {"id": pub_result.id, "message": "Publisher preset created successfully"}, 200

    @auth_required("CONFIG_PUBLISHER_UPDATE")
    def put(self, preset_id: str | None = None):
        if preset_id is None:
            return {"error": "No preset_id provided"}, 400
        response, status = publisher_preset.PublisherPreset.update(preset_id, request.json)
        _invalidate_admin_cache(status)
        return response, status

    @auth_required("CONFIG_PUBLISHER_DELETE")
    def delete(self, preset_id: str | None = None):
        if preset_id is None:
            return {"error": "No preset_id provided"}, 400
        response, status = publisher_preset.PublisherPreset.delete(preset_id)
        _invalidate_admin_cache(status)
        return response, status


class WordLists(MethodView):
    @auth_required("CONFIG_WORD_LIST_ACCESS")
    @extract_args("search", "usage", "with_entries", "page", "limit", "sort", "order", "fetch_all")
    def get(self, word_list_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if word_list_id:
            return word_list.WordList.get_for_api(word_list_id)
        return word_list.WordList.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self):
        wordlist = word_list.WordList.add(request.json)
        _invalidate_admin_cache(200)
        return {"id": wordlist.id, "message": "Word list created successfully"}, 200

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id: int | None = None):
        if word_list_id is None:
            return {"error": "No word_list_id provided"}, 400
        try:
            response, status = word_list.WordList.delete(word_list_id)
            _invalidate_admin_cache(status)
            return response, status
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception(f"Failed to delete word list {word_list_id}")
            return {"error": "Could not delete word list"}, 400

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id: int | None = None):
        if word_list_id is None:
            return {"error": "No word_list_id provided"}, 400
        if data := request.json:
            response, status = word_list.WordList.update(word_list_id, data)
            _invalidate_admin_cache(status)
            return response, status
        return {"error": "No data provided"}, 400


class WordListImport(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def post(self):
        try:
            wls = None
            if file := request.files.get("file"):
                wls = word_list.WordList.import_word_lists(file)
            if json_data := request.get_json(silent=True):
                wls = word_list.WordList.import_word_lists_from_json(json_data)
            if wls is None:
                logger.error("Failed to import Word Lists")
                return {"error": "Unable to import Word Lists"}, 400

            for wl in wls:
                queue_manager.queue_manager.gather_word_list(wl.id)

            _invalidate_admin_cache(200)
            return {"word_lists": [wl.id for wl in wls], "count": len(wls), "message": "Successfully imported word lists"}
        except ValueError as exc:
            logger.warning(f"Invalid word list import payload: {exc}")
            return {"error": str(exc)}, 400
        except Exception:
            logger.exception("Exception occurred during Word List import")
            return {"error": "Unable to import Word Lists"}, 500


class WordListExport(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def get(self):
        word_list_ids = request.args.getlist("ids")
        data = word_list.WordList.export(word_list_ids)
        if data is None:
            return {"error": "Unable to export word lists"}, 400
        return send_file(
            io.BytesIO(data),
            download_name="word_list_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class WordListGather(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def post(self, word_list_id: int | None = None):
        if not word_list_id:
            return queue_manager.queue_manager.gather_all_word_lists()
        return queue_manager.queue_manager.gather_word_list(word_list_id)


class WorkerInstances(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.ping_workers()


class Workers(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    @extract_args("search", "category", "type", "exclude", "page", "limit", "sort", "order", "fetch_all")
    def get(self, worker_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if worker_id:
            return worker.Worker.get_for_api(worker_id)
        if Config.DISABLE_PPN_COLLECTOR:
            if filter_args:
                filter_args["exclude"] = "ppn"
            else:
                filter_args = {"exclude": "ppn"}
        return worker.Worker.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_WORKER_ACCESS")
    def patch(self, worker_id: str | None = None):
        if worker_id is None:
            return {"error": "No worker_id provided"}, 400
        if not request.json:
            return {"error": "No data provided"}, 400
        if update_worker := worker.Worker.get(worker_id):
            return update_worker.update(request.json)
        return {"error": "Worker not found"}, 404


def build_config_blueprint(name: str) -> Blueprint:
    config_bp = Blueprint(name, __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/{name}")
    crud_methods = ["GET", "PUT", "DELETE"]
    crud_patch_methods = ["GET", "PUT", "DELETE", "PATCH"]

    config_bp.add_url_rule("/acls", view_func=ACLEntries.as_view(f"{name}_acls"))
    config_bp.add_url_rule("/acls/<int:acl_id>", view_func=ACLEntries.as_view(f"{name}_acl"), methods=crud_methods)
    config_bp.add_url_rule("/attributes", view_func=Attributes.as_view(f"{name}_attributes"))
    config_bp.add_url_rule("/attributes/<int:attribute_id>", view_func=Attributes.as_view(f"{name}_attribute"), methods=crud_methods)
    config_bp.add_url_rule("/bots", view_func=Bots.as_view(f"{name}_bots_config"))
    config_bp.add_url_rule("/bots/<string:bot_id>", view_func=Bots.as_view(f"{name}_bot_config"), methods=crud_methods)
    config_bp.add_url_rule("/bots/<string:bot_id>/execute", view_func=BotExecute.as_view(f"{name}_bot_execute"))
    config_bp.add_url_rule(
        "/dictionaries-reload/<string:dictionary_type>", view_func=DictionariesReload.as_view(f"{name}_dictionaries_reload")
    )
    config_bp.add_url_rule("/organizations", view_func=Organizations.as_view(f"{name}_organizations"))
    config_bp.add_url_rule(
        "/organizations/<int:organization_id>",
        view_func=Organizations.as_view(f"{name}_organization"),
        methods=crud_methods,
    )
    config_bp.add_url_rule("/osint-sources", view_func=OSINTSources.as_view(f"{name}_osint_sources"))
    config_bp.add_url_rule("/sources", view_func=OSINTSources.as_view(f"{name}_sources"))
    config_bp.add_url_rule(
        "/osint-sources/<string:source_id>", view_func=OSINTSources.as_view(f"{name}_osint_source"), methods=crud_patch_methods
    )
    config_bp.add_url_rule("/sources/<string:source_id>", view_func=OSINTSources.as_view(f"{name}_source"), methods=crud_patch_methods)
    config_bp.add_url_rule("/osint-sources/<string:source_id>/collect", view_func=OSINTSourceCollect.as_view(f"{name}_osint_source_collect"))
    config_bp.add_url_rule("/osint-sources/collect", view_func=OSINTSourceCollect.as_view(f"{name}_osint_sources_collect"))
    config_bp.add_url_rule("/osint-sources/<string:source_id>/preview", view_func=OSINTSourcePreview.as_view(f"{name}_osint_source_preview"))
    config_bp.add_url_rule("/osint-source-groups", view_func=OSINTSourceGroups.as_view(f"{name}_osint_source_groups_config"))
    config_bp.add_url_rule(
        "/osint-source-groups/<string:group_id>", view_func=OSINTSourceGroups.as_view(f"{name}_osint_source_group"), methods=crud_methods
    )
    config_bp.add_url_rule("/export-osint-sources", view_func=OSINTSourcesExport.as_view(f"{name}_osint_sources_export"))
    config_bp.add_url_rule("/import-osint-sources", view_func=OSINTSourcesImport.as_view(f"{name}_osint_sources_import"))
    config_bp.add_url_rule("/parameters", view_func=Parameters.as_view(f"{name}_parameters"))
    config_bp.add_url_rule("/worker-parameters", view_func=WorkerParameters.as_view(f"{name}_worker_parameters"))
    config_bp.add_url_rule("/permissions", view_func=Permissions.as_view(f"{name}_permissions"))
    config_bp.add_url_rule("/presenters", view_func=Presenters.as_view(f"{name}_presenters"))
    config_bp.add_url_rule("/product-types", view_func=ProductTypes.as_view(f"{name}_product_types_config"))
    config_bp.add_url_rule("/product-types/<int:type_id>", view_func=ProductTypes.as_view(f"{name}_product_type"), methods=crud_methods)
    config_bp.add_url_rule("/templates", view_func=Templates.as_view(f"{name}_templates"))
    config_bp.add_url_rule("/templates/<string:template_path>", view_func=Templates.as_view(f"{name}_template"))
    config_bp.add_url_rule("/templates/validate", view_func=TemplateValidation.as_view(f"{name}_template_validation"))
    config_bp.add_url_rule("/publishers", view_func=Publishers.as_view(f"{name}_publishers"))
    config_bp.add_url_rule("/publishers-presets", view_func=PublisherPresets.as_view(f"{name}_publishers_presets"))
    config_bp.add_url_rule(
        "/publishers-presets/<string:preset_id>", view_func=PublisherPresets.as_view(f"{name}_publishers_preset"), methods=crud_methods
    )
    config_bp.add_url_rule("/publisher-presets", view_func=PublisherPresets.as_view(f"{name}_publisher_presets"))
    config_bp.add_url_rule(
        "/publisher-presets/<string:preset_id>", view_func=PublisherPresets.as_view(f"{name}_publisher_preset"), methods=crud_methods
    )
    config_bp.add_url_rule("/report-item-types", view_func=ReportItemTypes.as_view(f"{name}_report_item_types"))
    config_bp.add_url_rule(
        "/report-item-types/<int:type_id>", view_func=ReportItemTypes.as_view(f"{name}_report_item_type"), methods=crud_methods
    )
    config_bp.add_url_rule("/export-report-item-types", view_func=ReportItemTypesExport.as_view(f"{name}_report_item_types_export"))
    config_bp.add_url_rule("/import-report-item-types", view_func=ReportItemTypesImport.as_view(f"{name}_report_item_types_import"))
    config_bp.add_url_rule("/roles", view_func=Roles.as_view(f"{name}_roles"))
    config_bp.add_url_rule("/roles/<int:role_id>", view_func=Roles.as_view(f"{name}_role"), methods=crud_methods)
    config_bp.add_url_rule("/users", view_func=Users.as_view(f"{name}_users"))
    config_bp.add_url_rule("/users-import", view_func=UsersImport.as_view(f"{name}_users_import"))
    config_bp.add_url_rule("/users-export", view_func=UsersExport.as_view(f"{name}_users_export"))
    config_bp.add_url_rule("/users/<int:user_id>", view_func=Users.as_view(f"{name}_user"), methods=crud_methods)
    config_bp.add_url_rule("/word-lists", view_func=WordLists.as_view(f"{name}_word_lists"))
    config_bp.add_url_rule("/word-lists/<int:word_list_id>", view_func=WordLists.as_view(f"{name}_word_list"), methods=crud_methods)
    config_bp.add_url_rule("/word-lists/gather/<int:word_list_id>", view_func=WordListGather.as_view(f"{name}_word_list_gather"))
    config_bp.add_url_rule("/word-lists/gather", view_func=WordListGather.as_view(f"{name}_word_list_gather_all"))
    config_bp.add_url_rule("/export-word-lists", view_func=WordListExport.as_view(f"{name}_word_list_export"))
    config_bp.add_url_rule("/import-word-lists", view_func=WordListImport.as_view(f"{name}_word_list_import"))
    config_bp.add_url_rule("/workers", view_func=WorkerInstances.as_view(f"{name}_workers"))
    config_bp.add_url_rule("/workers/cron-jobs", view_func=CronJobs.as_view(f"{name}_cron_jobs"))
    config_bp.add_url_rule("/workers/schedule", view_func=Schedule.as_view(f"{name}_queue_schedule_config"))
    config_bp.add_url_rule("/workers/tasks", view_func=QueueTasks.as_view(f"{name}_queue_tasks"))
    config_bp.add_url_rule("/workers/queue-status", view_func=QueueStatus.as_view(f"{name}_queue_status"))
    config_bp.add_url_rule("/workers/active", view_func=ActiveJobs.as_view(f"{name}_active_jobs"))
    config_bp.add_url_rule("/workers/failed", view_func=FailedJobs.as_view(f"{name}_failed_jobs"))
    config_bp.add_url_rule("/workers/stats", view_func=WorkerStats.as_view(f"{name}_worker_stats"))
    config_bp.add_url_rule("/workers/dashboard", view_func=SchedulerDashboard.as_view(f"{name}_scheduler_dashboard"))
    config_bp.add_url_rule("/schedule", view_func=Schedule.as_view(f"{name}_queue_schedule"))
    config_bp.add_url_rule("/schedule/<string:task_id>", view_func=Schedule.as_view(f"{name}_queue_schedule_task"))
    config_bp.add_url_rule("/worker-types", view_func=Workers.as_view(f"{name}_worker_types"))
    config_bp.add_url_rule("/worker-types/<string:worker_id>", view_func=Workers.as_view(f"{name}_worker_type_patch"))
    config_bp.add_url_rule("/connectors", view_func=Connectors.as_view(f"{name}_connectors"))
    config_bp.add_url_rule("/connectors/<string:connector_id>", view_func=Connectors.as_view(f"{name}_connector"), methods=crud_patch_methods)
    config_bp.add_url_rule("/connectors/<string:connector_id>/pull", view_func=ConnectorsPull.as_view(f"{name}_connector_collect"))

    return config_bp


def initialize(app: Flask):
    config_bp = build_config_blueprint("config")
    admin_bp = build_config_blueprint("admin")

    app.register_blueprint(config_bp)
    app.register_blueprint(admin_bp)
