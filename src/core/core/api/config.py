import base64
import io
from typing import Any

from flask import Blueprint, Flask, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import current_user
from psycopg.errors import NotNullViolation, UniqueViolation  # noqa: F401
from sqlalchemy.exc import IntegrityError  # noqa: F401

from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.managers.data_manager import (
    delete_template,
)
from core.managers.db_manager import db
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

# Project import for shared template logic
from core.service.template_crud import create_or_update_template
from core.service.template_service import build_template_response, build_templates_list, invalidate_template_validation_cache
from core.service.template_validation import validate_template_content


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


class DictionariesReload(MethodView):
    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def post(self, dictionary_type: str):
        attribute.Attribute.load_dictionaries(dictionary_type)
        return {"message": "success"}, 200


class ACLEntries(MethodView):
    @auth_required("CONFIG_ACL_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, acl_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if acl_id:
            return role_based_access.RoleBasedAccess.get_for_api(acl_id)
        return role_based_access.RoleBasedAccess.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self):
        acl = role_based_access.RoleBasedAccess.add(request.json)
        return {"message": "ACL created", "id": acl.id}, 201

    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id: int):
        return role_based_access.RoleBasedAccess.update(acl_id, request.json)

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id: int):
        return role_based_access.RoleBasedAccess.delete(acl_id)


class Attributes(MethodView):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS", "ANALYZE_ACCESS"])
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, attribute_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if attribute_id:
            return attribute.Attribute.get_for_api(attribute_id)

        return attribute.Attribute.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self):
        attribute_result = attribute.Attribute.add(request.json)
        return {"message": "Attribute added", "id": attribute_result.id}, 201

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id: int):
        return attribute.Attribute.update(attribute_id, request.json)

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id: int):
        return attribute.Attribute.delete(attribute_id)


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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, type_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if type_id:
            return report_item_type.ReportItemType.get_for_api(type_id)
        return report_item_type.ReportItemType.get_all_for_api(filter_args, True, current_user)

    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self):
        try:
            item = report_item_type.ReportItemType.add(request.json)
            return {"message": f"ReportItemType {item.title} added", "id": item.id}, 201
        except Exception:
            logger.exception("Failed to add report item type")
            return {"error": "Failed to add report item type"}, 500

    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id: int):
        if item := report_item_type.ReportItemType.update(type_id, request.json):
            return {"message": f"Report item type {item.title} updated", "id": f"{item.id}"}, 200
        return {"error": f"Report item type with ID: {type_id} not found"}, 404

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id: int):
        return report_item_type.ReportItemType.delete(type_id)


class ProductTypes(MethodView):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, type_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if type_id:
            return product_type.ProductType.get_for_api(type_id)
        return product_type.ProductType.get_all_for_api(filter_args, True, current_user)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        try:
            product = product_type.ProductType.add(request.json)
            return {"message": "Product type created", "id": product.id}, 201
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception as e:
            logger.error(f"Error creating product type: {e}")
            return {"error": "Failed to create product type"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id: int):
        try:
            return product_type.ProductType.update(type_id, request.json, current_user)
        except Exception as e:
            logger.error(f"Error updating product type: {e}")
            return {"error": "Failed to update product type"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id: int):
        try:
            return product_type.ProductType.delete(type_id)
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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, filter_args: dict[str, Any] | None = None):
        return Permission.get_all_for_api(filter_args, True)


class Roles(MethodView):
    @auth_required("CONFIG_ROLE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, role_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if role_id:
            return role.Role.get_for_api(role_id)
        return role.Role.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        new_role = role.Role.add(request.json)
        return {"message": "Role created", "id": new_role.id}, 201

    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id: int):
        if data := request.json:
            return role.Role.update(role_id, data)
        return {"error": "No data provided"}, 400

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id: int):
        if user.UserRole.has_assigned_user(role_id):
            logger.warning(f"Role {role_id} cannot be deleted, it has assigned users")
            return {"error": f"Role {role_id} cannot be deleted, it has assigned users"}, 400
        return role.Role.delete(role_id)


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
        return create_or_update_template(template_id, base64_content)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def put(self, template_path: str):
        # Use shared logic for create/update
        if not request.json:
            return {"error": "No data provided"}, 400
        base64_content = request.json.get("content")
        invalidate_template_validation_cache(template_path)
        return create_or_update_template(template_path, base64_content)

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, template_path: str):
        invalidate_template_validation_cache(template_path)
        if delete_template(template_path):
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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, organization_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if organization_id:
            return organization.Organization.get_for_api(organization_id)
        return organization.Organization.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self):
        org = organization.Organization.add(request.json)
        return {"message": "Organization created", "id": org.id}, 201

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id: int):
        return organization.Organization.update(organization_id, request.json)

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id: int):
        return organization.Organization.delete(organization_id)


class UsersImport(MethodView):
    @auth_required("CONFIG_USER_UPDATE")
    def post(self):
        user_list = request.json
        if not isinstance(user_list, list):
            return {"error": "Invalid data format"}, 400
        if users := user.User.import_users(user_list):
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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, user_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if user_id:
            return user.User.get_for_api(user_id)
        return user.User.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_USER_CREATE")
    def post(self):
        try:
            new_user = user.User.add(request.json)
            return {"message": f"User {new_user.username} created", "id": new_user.id}, 201
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception()
            return {"error": "Could not create user"}, 400

    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id: int):
        try:
            return user.User.update(user_id, request.json)
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception()
            return {"error": "Could not update user"}, 400

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id: int):
        try:
            return user.User.delete(user_id)
        except Exception:
            logger.exception()
            return {"error": "Could not delete user"}, 400


class Bots(MethodView):
    @auth_required("CONFIG_BOT_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, bot_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if bot_id:
            return bot.Bot.get_for_api(bot_id)
        return bot.Bot.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_BOT_UPDATE")
    def put(self, bot_id: str):
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if updated_bot := bot.Bot.update(bot_id, update_data):
                logger.debug(f"Successfully updated {updated_bot}")
                return {"message": f"Successfully upated {updated_bot.name}", "id": f"{updated_bot.id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 500
        return {"error": f"Bot with ID: {bot_id} not found"}, 404

    @auth_required("CONFIG_BOT_CREATE")
    def post(self):
        new_bot = bot.Bot.add(request.json)
        return {"message": f"Bot {new_bot.name} created", "id": new_bot.id}, 201

    @auth_required("CONFIG_BOT_DELETE")
    def delete(self, bot_id: str):
        return bot.Bot.delete(bot_id)


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
        """Get all cron job configurations for the RQ scheduler.

        Returns a list of cron job configurations including:
        - OSINT source collectors
        - Bots
        - Housekeeping tasks

        Returns:
            list: List of cron job configurations with task, queue, args, cron schedule, and task_id
        """
        try:
            cron_jobs = []

            # Get OSINT source collectors
            sources = osint_source.OSINTSource.get_all_for_collector()
            for source in sources:
                cron_schedule = source.get_schedule()
                if not cron_schedule:
                    continue

                cron_jobs.append(
                    {
                        "task": "collector_task",
                        "queue": "collectors",
                        "args": [source.id, False],  # manual=False for scheduled jobs
                        "cron": cron_schedule,
                        "task_id": source.task_id,
                        "name": source.name,
                    }
                )

            # Get Bot tasks
            stmt = db.select(bot.Bot).where(bot.Bot.enabled)
            bots = db.session.execute(stmt).scalars().all()
            for bot_item in bots:
                cron_schedule = bot_item.get_schedule()
                if not cron_schedule:
                    continue

                cron_jobs.append(
                    {
                        "task": "bot_task",
                        "queue": "bots",
                        "args": [bot_item.id],
                        "cron": cron_schedule,
                        "task_id": bot_item.task_id,
                        "name": bot_item.name,
                    }
                )

            # Add housekeeping cron jobs
            cron_jobs.append(
                {
                    "task": "cleanup_token_blacklist",
                    "queue": "misc",
                    "args": [],
                    "cron": "0 2 * * *",
                    "task_id": "cleanup_token_blacklist",
                    "name": "Cleanup Token Blacklist",
                }
            )

            return {"cron_jobs": cron_jobs}, 200

        except Exception:
            logger.exception("Failed to get cron job configurations")
            return {"error": "Failed to get cron job configurations"}, 500


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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, connector_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if connector_id:
            return connector.Connector.get_for_api(connector_id)
        return connector.Connector.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_CONNECTOR_CREATE")
    def post(self):
        if source := connector.Connector.add(request.json):
            return {"id": source.id, "message": "Connector created successfully"}, 201
        return {"error": "Connector could not be created"}, 400

    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def put(self, connector_id: str):
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if source := connector.Connector.update(connector_id, update_data):
                return {"message": f"Connector {source.name} updated", "id": f"{connector_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 500
        return {"error": f"Connector with ID: {connector_id} not found"}, 404

    @auth_required("CONFIG_CONNECTOR_DELETE")
    def delete(self, connector_id: str):
        # TODO: Implement force delete logic if needed
        return connector.Connector.delete(connector_id)

    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def patch(self, connector_id: str):
        # TODO: Implement toggle state logic if needed
        pass


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
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, source_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if source_id:
            return osint_source.OSINTSource.get_for_api(source_id)
        return osint_source.OSINTSource.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        try:
            if source := osint_source.OSINTSource.add(request.json):
                return {"id": source.id, "message": "OSINT source created successfully"}, 201
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return {"error": "OSINT source could not be created"}, 400

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id: str):
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if source := osint_source.OSINTSource.update(source_id, update_data):
                return {"message": f"OSINT Source {source.name} updated", "id": f"{source_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 400
        return {"error": f"OSINT Source with ID: {source_id} not found"}, 404

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id: str):
        force = request.args.get("force", default=False, type=bool)
        if not force:
            from core.service.news_item import NewsItemService as _NewsItemService

            if _NewsItemService.has_related_news_items(source_id):
                return {
                    "error": f"""OSINT Source with ID: {source_id} has related News Items.
                To delete this item and all related News Items, set the 'force' flag."""
                }, 409

        return osint_source.OSINTSource.delete(source_id, force=force)

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def patch(self, source_id: str):
        if request.json:
            state = request.json.get("state")
        else:
            state = request.args.get("state", default="enabled", type=str)
        logger.debug(f"Toggling OSINT source {source_id} to state {state}")
        return osint_source.OSINTSource.toggle_state(source_id, state)


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
        sources = None
        if file := request.files.get("file"):
            sources = osint_source.OSINTSource.import_osint_sources(file)
        if json_data := request.get_json(silent=True):
            sources = osint_source.OSINTSource.import_osint_sources_from_json(json_data)
        if sources is None:
            logger.error("Failed to import OSINT sources")
            return {"error": "Unable to import"}, 400
        return {"sources": sources, "count": len(sources), "message": "Successfully imported sources"}


class OSINTSourceGroups(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, group_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if group_id:
            return osint_source.OSINTSourceGroup.get_for_api(group_id)
        return osint_source.OSINTSourceGroup.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        source_group = osint_source.OSINTSourceGroup.add(request.json)
        return {"id": source_group.id, "message": "OSINT source group created successfully"}, 200

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id: str):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        return osint_source.OSINTSourceGroup.update(group_id, data, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id: str):
        return osint_source.OSINTSourceGroup.delete(group_id)


class TaskResults(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, task_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if task_id:
            return task.Task.get_for_api(task_id)
        result, status = task.Task.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)
        if status != 200:
            return result, status

        stats = task.Task.get_task_statistics()
        result.update(stats)
        return result, status

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def delete(self, task_id: str):
        return task.Task.delete(task_id)


class Presenters(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, filter_args: dict[str, Any] | None = None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class Publishers(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, filter_args: dict[str, Any] | None = None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class PublisherPresets(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order")
    def get(self, preset_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if preset_id:
            return publisher_preset.PublisherPreset.get_for_api(preset_id)
        return publisher_preset.PublisherPreset.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_PUBLISHER_CREATE")
    def post(self):
        pub_result = publisher_preset.PublisherPreset.add(request.json)
        return {"id": pub_result.id, "message": "Publisher preset created successfully"}, 200

    @auth_required("CONFIG_PUBLISHER_UPDATE")
    def put(self, preset_id: str):
        return publisher_preset.PublisherPreset.update(preset_id, request.json)

    @auth_required("CONFIG_PUBLISHER_DELETE")
    def delete(self, preset_id: str):
        return publisher_preset.PublisherPreset.delete(preset_id)


class WordLists(MethodView):
    @auth_required("CONFIG_WORD_LIST_ACCESS")
    @extract_args("search", "usage", "with_entries", "page", "limit", "sort", "order")
    def get(self, word_list_id: int | None = None, filter_args: dict[str, Any] | None = None):
        if word_list_id:
            return word_list.WordList.get_for_api(word_list_id)
        return word_list.WordList.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self):
        wordlist = word_list.WordList.add(request.json)
        return {"id": wordlist.id, "message": "Word list created successfully"}, 200

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id: int):
        try:
            return word_list.WordList.delete(word_list_id)
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception(f"Failed to delete word list {word_list_id}")
            return {"error": "Could not delete word list"}, 400

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id: int):
        if data := request.json:
            return word_list.WordList.update(word_list_id, data)
        return {"error": "No data provided"}, 400


class WordListImport(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def post(self):
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

        return {"word_lists": [wl.id for wl in wls], "count": len(wls), "message": "Successfully imported word lists"}


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
    @extract_args("search", "category", "type", "exclude", "page", "limit", "sort", "order")
    def get(self, filter_args: dict[str, Any] | None = None):
        if Config.DISABLE_PPN_COLLECTOR:
            if filter_args:
                filter_args["exclude"] = "ppn"
            else:
                filter_args = {"exclude": "ppn"}
        return worker.Worker.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_WORKER_ACCESS")
    def patch(self, worker_id: str):
        if not request.json:
            return {"error": "No data provided"}, 400
        if update_worker := worker.Worker.get(worker_id):
            return update_worker.update(request.json)
        return {"error": "Worker not found"}, 404


def initialize(app: Flask):
    config_bp = Blueprint("config", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/config")

    config_bp.add_url_rule("/acls", view_func=ACLEntries.as_view("acls"))
    config_bp.add_url_rule("/acls/<int:acl_id>", view_func=ACLEntries.as_view("acl"))
    config_bp.add_url_rule("/attributes", view_func=Attributes.as_view("attributes"))
    config_bp.add_url_rule("/attributes/<int:attribute_id>", view_func=Attributes.as_view("attribute"))
    config_bp.add_url_rule("/bots", view_func=Bots.as_view("bots_config"))
    config_bp.add_url_rule("/bots/<string:bot_id>", view_func=Bots.as_view("bot_config"))
    config_bp.add_url_rule("/bots/<string:bot_id>/execute", view_func=BotExecute.as_view("bot_execute"))
    config_bp.add_url_rule("/dictionaries-reload/<string:dictionary_type>", view_func=DictionariesReload.as_view("dictionaries_reload"))
    config_bp.add_url_rule("/organizations", view_func=Organizations.as_view("organizations"))
    config_bp.add_url_rule("/organizations/<int:organization_id>", view_func=Organizations.as_view("organization"))
    config_bp.add_url_rule("/osint-sources", view_func=OSINTSources.as_view("osint_sources"))
    config_bp.add_url_rule("/osint-sources/<string:source_id>", view_func=OSINTSources.as_view("osint_source"))
    config_bp.add_url_rule("/osint-sources/<string:source_id>/collect", view_func=OSINTSourceCollect.as_view("osint_source_collect"))
    config_bp.add_url_rule("/osint-sources/collect", view_func=OSINTSourceCollect.as_view("osint_sources_collect"))
    config_bp.add_url_rule("/osint-sources/<string:source_id>/preview", view_func=OSINTSourcePreview.as_view("osint_source_preview"))
    config_bp.add_url_rule("/osint-source-groups", view_func=OSINTSourceGroups.as_view("osint_source_groups_config"))
    config_bp.add_url_rule("/osint-source-groups/<string:group_id>", view_func=OSINTSourceGroups.as_view("osint_source_group"))
    config_bp.add_url_rule("/export-osint-sources", view_func=OSINTSourcesExport.as_view("osint_sources_export"))
    config_bp.add_url_rule("/import-osint-sources", view_func=OSINTSourcesImport.as_view("osint_sources_import"))
    config_bp.add_url_rule("/parameters", view_func=Parameters.as_view("parameters"))
    config_bp.add_url_rule("/worker-parameters", view_func=WorkerParameters.as_view("worker_parameters"))
    config_bp.add_url_rule("/permissions", view_func=Permissions.as_view("permissions"))
    config_bp.add_url_rule("/presenters", view_func=Presenters.as_view("presenters"))
    config_bp.add_url_rule("/product-types", view_func=ProductTypes.as_view("product_types_config"))
    config_bp.add_url_rule("/product-types/<int:type_id>", view_func=ProductTypes.as_view("product_type"))
    config_bp.add_url_rule("/templates", view_func=Templates.as_view("templates"))
    config_bp.add_url_rule("/templates/<string:template_path>", view_func=Templates.as_view("template"))
    config_bp.add_url_rule("/templates/validate", view_func=TemplateValidation.as_view("template_validation"))
    config_bp.add_url_rule("/publishers", view_func=Publishers.as_view("publishers"))
    config_bp.add_url_rule("/publishers-presets", view_func=PublisherPresets.as_view("publishers_presets"))
    config_bp.add_url_rule("/publishers-presets/<string:preset_id>", view_func=PublisherPresets.as_view("publishers_preset"))
    config_bp.add_url_rule("/publisher-presets", view_func=PublisherPresets.as_view("publisher_presets"))
    config_bp.add_url_rule("/publisher-presets/<string:preset_id>", view_func=PublisherPresets.as_view("publisher_preset"))
    config_bp.add_url_rule("/task-results", view_func=TaskResults.as_view("task_results"))
    config_bp.add_url_rule("/task-results/<string:task_id>", view_func=TaskResults.as_view("task_result"))

    config_bp.add_url_rule("/report-item-types", view_func=ReportItemTypes.as_view("report_item_types"))
    config_bp.add_url_rule("/report-item-types/<int:type_id>", view_func=ReportItemTypes.as_view("report_item_type"))
    config_bp.add_url_rule("/export-report-item-types", view_func=ReportItemTypesExport.as_view("report_item_types_export"))
    config_bp.add_url_rule("/import-report-item-types", view_func=ReportItemTypesImport.as_view("report_item_types_import"))
    config_bp.add_url_rule("/roles", view_func=Roles.as_view("roles"))
    config_bp.add_url_rule("/roles/<int:role_id>", view_func=Roles.as_view("role"))
    config_bp.add_url_rule("/users", view_func=Users.as_view("users"))
    config_bp.add_url_rule("/users-import", view_func=UsersImport.as_view("users_import"))
    config_bp.add_url_rule("/users-export", view_func=UsersExport.as_view("users_export"))
    config_bp.add_url_rule("/users/<int:user_id>", view_func=Users.as_view("user"))
    config_bp.add_url_rule("/word-lists", view_func=WordLists.as_view("word_lists"))
    config_bp.add_url_rule("/word-lists/<int:word_list_id>", view_func=WordLists.as_view("word_list"))
    config_bp.add_url_rule("/word-lists/gather/<int:word_list_id>", view_func=WordListGather.as_view("word_list_gather"))
    config_bp.add_url_rule("/word-lists/gather", view_func=WordListGather.as_view("word_list_gather_all"))
    config_bp.add_url_rule("/export-word-lists", view_func=WordListExport.as_view("word_list_export"))
    config_bp.add_url_rule("/import-word-lists", view_func=WordListImport.as_view("word_list_import"))
    config_bp.add_url_rule("/workers", view_func=WorkerInstances.as_view("workers"))
    config_bp.add_url_rule("/workers/cron-jobs", view_func=CronJobs.as_view("cron_jobs"))
    config_bp.add_url_rule("/workers/schedule", view_func=Schedule.as_view("queue_schedule_config"))
    config_bp.add_url_rule("/workers/tasks", view_func=QueueTasks.as_view("queue_tasks"))
    config_bp.add_url_rule("/workers/queue-status", view_func=QueueStatus.as_view("queue_status"))
    config_bp.add_url_rule("/workers/active", view_func=ActiveJobs.as_view("active_jobs"))
    config_bp.add_url_rule("/workers/failed", view_func=FailedJobs.as_view("failed_jobs"))
    config_bp.add_url_rule("/workers/stats", view_func=WorkerStats.as_view("worker_stats"))
    config_bp.add_url_rule("/workers/dashboard", view_func=SchedulerDashboard.as_view("scheduler_dashboard"))
    config_bp.add_url_rule("/schedule", view_func=Schedule.as_view("queue_schedule"))
    config_bp.add_url_rule("/schedule/<string:task_id>", view_func=Schedule.as_view("queue_schedule_task"))
    config_bp.add_url_rule("/worker-types", view_func=Workers.as_view("worker_types"))
    config_bp.add_url_rule("/worker-types/<string:worker_id>", view_func=Workers.as_view("worker_type_patch"))
    config_bp.add_url_rule("/connectors", view_func=Connectors.as_view("connectors"))
    config_bp.add_url_rule("/connectors/<string:connector_id>", view_func=Connectors.as_view("connector"))
    config_bp.add_url_rule("/connectors/<string:connector_id>/pull", view_func=ConnectorsPull.as_view("connector_collect"))

    app.register_blueprint(config_bp)
