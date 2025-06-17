import io
from flask import Blueprint, request, send_file, jsonify, Flask
from flask.views import MethodView
from flask_jwt_extended import current_user
from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation

from core.managers import queue_manager
from core.log import logger
from core.managers.auth_manager import auth_required
from core.managers.data_manager import (
    get_for_api,
    write_base64_to_file,
    get_presenter_templates,
    delete_template,
    get_templates_as_base64,
)
from core.model import (
    attribute,
    bot,
    product_type,
    publisher_preset,
    organization,
    osint_source,
    connector,
    report_item_type,
    role,
    role_based_access,
    user,
    word_list,
    task,
    worker,
)
from core.model.news_item_conflict import NewsItemConflict
from core.model.story_conflict import StoryConflict
from core.service.news_item import NewsItemService
from core.model.permission import Permission
from core.managers.decorators import extract_args
from core.managers import schedule_manager
from core.config import Config


def convert_integrity_error(error: IntegrityError) -> str:
    """
    Converts an IntegrityError into a more descriptive ValidationError.
    Currently handles UniqueViolation errors using psycopg2's diagnostics.
    """
    orig = error.orig
    if isinstance(orig, UniqueViolation):
        constraint = orig.diag.constraint_name
        field = constraint.split("_")[1] if constraint else None
        if field:
            return f"A record with this {field} already exists."
    return str(error)


class DictionariesReload(MethodView):
    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def post(self, dictionary_type):
        attribute.Attribute.load_dictionaries(dictionary_type)
        return {"message": "success"}, 200


class ACLEntries(MethodView):
    @auth_required("CONFIG_ACL_ACCESS")
    @extract_args("search")
    def get(self, acl_id=None, filter_args=None):
        if acl_id:
            return role_based_access.RoleBasedAccess.get_for_api(acl_id)
        return role_based_access.RoleBasedAccess.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self):
        acl = role_based_access.RoleBasedAccess.add(request.json)
        return {"message": "ACL created", "id": acl.id}, 201

    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id):
        return role_based_access.RoleBasedAccess.update(acl_id, request.json)

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id):
        return role_based_access.RoleBasedAccess.delete(acl_id)


class Attributes(MethodView):
    @auth_required(["CONFIG_ATTRIBUTE_ACCESS", "ANALYZE_ACCESS"])
    @extract_args("search")
    def get(self, attribute_id=None, filter_args=None):
        if attribute_id:
            return attribute.Attribute.get_for_api(attribute_id)

        return attribute.Attribute.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self):
        attribute_result = attribute.Attribute.add(request.json)
        return {"message": "Attribute added", "id": attribute_result.id}, 201

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id):
        return attribute.Attribute.update(attribute_id, request.json)

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id):
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
    @extract_args("search")
    def get(self, type_id=None, filter_args=None):
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
    def put(self, type_id):
        if item := report_item_type.ReportItemType.update(type_id, request.json):
            return {"message": f"Report item type {item.title} updated", "id": f"{item.id}"}, 200
        return {"error": f"Report item type with ID: {type_id} not found"}, 404

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id):
        return report_item_type.ReportItemType.delete(type_id)


class ProductTypes(MethodView):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    @extract_args("search")
    def get(self, type_id=None, filter_args=None):
        if type_id:
            return product_type.ProductType.get_for_api(type_id)
        return product_type.ProductType.get_all_for_api(filter_args, True, current_user)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        product = product_type.ProductType.add(request.json)
        return {"message": "Product type created", "id": product.id}, 201

    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id):
        return product_type.ProductType.update(type_id, request.json, current_user)

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id):
        return product_type.ProductType.delete(type_id)


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
    @extract_args("search")
    def get(self, filter_args=None):
        return Permission.get_all_for_api(filter_args, True)


class Roles(MethodView):
    @auth_required("CONFIG_ROLE_ACCESS")
    @extract_args("search")
    def get(self, role_id=None, filter_args=None):
        if role_id:
            return role.Role.get_for_api(role_id)
        return role.Role.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        new_role = role.Role.add(request.json)
        return {"message": "Role created", "id": new_role.id}, 201

    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id):
        if data := request.json:
            return role.Role.update(role_id, data)
        return {"error": "No data provided"}, 400

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id):
        return role.Role.delete(role_id)


class Templates(MethodView):
    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self, template_path=None):
        if request.args.get("list", default=False, type=bool):
            templates = [{"path": t} for t in get_presenter_templates()]
            return jsonify({"total_count": len(templates), "items": templates})
        if template_path:
            template = get_for_api(template_path)
            return (template, 200) or ({"error": "Product type not found"}, 404)
        templates = get_templates_as_base64()
        return jsonify({"items": templates, "total_count": len(templates)}), 200

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self, template_path=None):
        if not request.json:
            return {"error": "No data provided"}, 400
        template_path = request.json.get("id")
        if write_base64_to_file(request.json.get("content"), template_path):
            return {"message": "Template updated or created", "path": template_path}, 200
        return {"error": "Could not write template to file"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def put(self, template_path: str):
        if not request.json:
            return {"error": "No data provided"}, 400
        if write_base64_to_file(request.json.get("content"), template_path):
            return {"message": "Template updated or created", "path": template_path}, 200
        return {"error": "Could not write template to file"}, 500

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, template_path: str):
        if delete_template(template_path):
            return {"message": "Template deleted", "path": template_path}, 200
        return {"error": "Could not delete template"}, 500


class Organizations(MethodView):
    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    @extract_args("search")
    def get(self, organization_id=None, filter_args=None):
        if organization_id:
            return organization.Organization.get_for_api(organization_id)
        return organization.Organization.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self):
        org = organization.Organization.add(request.json)
        return {"message": "Organization created", "id": org.id}, 201

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id):
        return organization.Organization.update(organization_id, request.json)

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id):
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
    @extract_args("search")
    def get(self, user_id=None, filter_args=None):
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
    def put(self, user_id):
        try:
            return user.User.update(user_id, request.json)
        except IntegrityError as e:
            return {"error": convert_integrity_error(e)}, 400
        except Exception:
            logger.exception()
            return {"error": "Could not update user"}, 400

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id):
        try:
            return user.User.delete(user_id)
        except Exception:
            logger.exception()
            return {"error": "Could not delete user"}, 400


class Bots(MethodView):
    @auth_required("CONFIG_BOT_ACCESS")
    @extract_args("search")
    def get(self, bot_id=None, filter_args=None):
        if bot_id:
            return bot.Bot.get_for_api(bot_id)
        return bot.Bot.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_BOT_UPDATE")
    def put(self, bot_id):
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
    def delete(self, bot_id):
        return bot.Bot.delete(bot_id)


class BotExecute(MethodView):
    @auth_required("BOT_EXECUTE")
    def post(self, bot_id):
        return queue_manager.queue_manager.execute_bot_task(bot_id)


class QueueStatus(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_queue_status()


class QueueTasks(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.get_queued_tasks()


class Schedule(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self, task_id: str | None = None):
        try:
            if task_id:
                if result := schedule_manager.schedule.get_periodic_task(task_id):
                    return result, 200
                return {"error": "Task not found"}, 404
            if schedules := schedule_manager.schedule.get_periodic_tasks():
                return schedules, 200
            return {"error": "No schedules found"}, 404
        except Exception:
            logger.exception()


class RefreshInterval(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def post(self):
        data = request.get_json()
        cron_expr = data.get("cron")
        if not cron_expr:
            return jsonify({"error": "Missing cron expression"}), 400
        try:
            fire_times = schedule_manager.schedule.get_next_n_fire_times_from_cron(cron_expr, n=3)
            formatted_times = [ft.isoformat(timespec="minutes") for ft in fire_times]
            return jsonify(formatted_times), 200
        except Exception as e:
            logger.exception(e)
            return jsonify({"error": "Failed to compute schedule"}), 500


class Connectors(MethodView):
    @auth_required("CONFIG_CONNECTOR_ACCESS")
    @extract_args("search")
    def get(self, connector_id=None, filter_args=None):
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
                return {"message": f"OSINT Source {source.name} updated", "id": f"{connector_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 500
        return {"error": f"OSINT Source with ID: {connector_id} not found"}, 404

    @auth_required("CONFIG_CONNECTOR_DELETE")
    def delete(self, connector_id: str):
        force = request.args.get("force", default=False, type=bool)
        if not force and NewsItemService.has_related_news_items(connector_id):
            return {
                "error": f"""OSINT Source with ID: {connector_id} has related News Items.
                To delete this item and all related News Items, set the 'force' flag."""
            }, 409

        return osint_source.OSINTSource.delete(connector_id, force=force)

    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def patch(self, source_id: str):
        state = request.args.get("state", default="enabled", type=str)
        return osint_source.OSINTSource.toggle_state(source_id, state)


class ConnectorsPull(MethodView):
    @auth_required("CONFIG_CONNECTOR_UPDATE")
    def post(self, connector_id):
        """Trigger collection of stories from the external system."""
        try:
            collected_stories = queue_manager.queue_manager.pull_from_connector(connector_id=connector_id)

            return {"message": "Stories successfully collected.", "data": collected_stories}, 200
        except Exception as e:
            return {"error": str(e)}, 500


class OSINTSources(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search")
    def get(self, source_id=None, filter_args=None):
        if source_id:
            return osint_source.OSINTSource.get_for_api(source_id)
        return osint_source.OSINTSource.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        if source := osint_source.OSINTSource.add(request.json):
            return {"id": source.id, "message": "OSINT source created successfully"}, 201
        return {"error": "OSINT source could not be created"}, 400

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id: str):
        if not (update_data := request.json):
            return {"error": "No update data passed"}, 400
        try:
            if source := osint_source.OSINTSource.update(source_id, update_data):
                return {"message": f"OSINT Source {source.name} updated", "id": f"{source_id}"}, 200
        except ValueError as e:
            return {"error": str(e)}, 500
        return {"error": f"OSINT Source with ID: {source_id} not found"}, 404

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id: str):
        force = request.args.get("force", default=False, type=bool)
        if not force and NewsItemService.has_related_news_items(source_id):
            return {
                "error": f"""OSINT Source with ID: {source_id} has related News Items.
                To delete this item and all related News Items, set the 'force' flag."""
            }, 409

        return osint_source.OSINTSource.delete(source_id, force=force)

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def patch(self, source_id: str):
        state = request.args.get("state", default="enabled", type=str)
        return osint_source.OSINTSource.toggle_state(source_id, state)


class OSINTSourceCollect(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def post(self, source_id=None):
        StoryConflict.flush_store()
        NewsItemConflict.flush_store()
        if source_id:
            return queue_manager.queue_manager.collect_osint_source(source_id)
        return queue_manager.queue_manager.collect_all_osint_sources()


class OSINTSourcePreview(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def get(self, source_id):
        task_id = f"source_preview_{source_id}"

        if result := task.Task.get(task_id):
            return result.to_dict(), 200
        return {"error": "Task not found"}, 404

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def post(self, source_id):
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
        if file := request.files.get("file"):
            sources = osint_source.OSINTSource.import_osint_sources(file)
            if sources is None:
                return {"error": "Unable to import"}, 400
            return {"sources": sources, "count": len(sources), "message": "Successfully imported sources"}
        return {"error": "No file provided"}, 400


class OSINTSourceGroups(MethodView):
    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    @extract_args("search")
    def get(self, group_id=None, filter_args=None):
        if group_id:
            return osint_source.OSINTSourceGroup.get_for_api(group_id)
        return osint_source.OSINTSourceGroup.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        source_group = osint_source.OSINTSourceGroup.add(request.json)
        return {"id": source_group.id, "message": "OSINT source group created successfully"}, 200

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id):
        if not (data := request.json):
            return {"error": "No data provided"}, 400
        return osint_source.OSINTSourceGroup.update(group_id, data, user=current_user)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id):
        return osint_source.OSINTSourceGroup.delete(group_id)


class Presenters(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search")
    def get(self, filter_args=None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class Publishers(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search")
    def get(self, filter_args=None):
        filter_args = filter_args or {}
        filter_args["category"] = "publisher"
        return worker.Worker.get_all_for_api(filter_args)


class PublisherPresets(MethodView):
    @auth_required("CONFIG_PUBLISHER_ACCESS")
    @extract_args("search")
    def get(self, preset_id=None, filter_args=None):
        if preset_id:
            return publisher_preset.PublisherPreset.get_for_api(preset_id)
        return publisher_preset.PublisherPreset.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_PUBLISHER_CREATE")
    def post(self):
        pub_result = publisher_preset.PublisherPreset.add(request.json)
        return {"id": pub_result.id, "message": "Publisher preset created successfully"}, 200

    @auth_required("CONFIG_PUBLISHER_UPDATE")
    def put(self, preset_id):
        return publisher_preset.PublisherPreset.update(preset_id, request.json)

    @auth_required("CONFIG_PUBLISHER_DELETE")
    def delete(self, preset_id):
        return publisher_preset.PublisherPreset.delete(preset_id)


class WordLists(MethodView):
    @auth_required("CONFIG_WORD_LIST_ACCESS")
    @extract_args("search", "usage", "with_entries")
    def get(self, word_list_id=None, filter_args: dict | None = None):
        if word_list_id:
            return word_list.WordList.get_for_api(word_list_id)
        return word_list.WordList.get_all_for_api(filter_args=filter_args, with_count=True, user=current_user)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self):
        wordlist = word_list.WordList.add(request.json)
        return {"id": wordlist.id, "message": "Word list created successfully"}, 200

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id):
        return word_list.WordList.delete(word_list_id)

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        if data := request.json:
            return word_list.WordList.update(word_list_id, data)
        return {"error": "No data provided"}, 400


class WordListImport(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def post(self):
        if file := request.files.get("file"):
            if wls := word_list.WordList.import_word_lists(file):
                return {"word_lists": [wl.id for wl in wls], "count": len(wls), "message": "Successfully imported word lists"}
            return {"error": "Unable to import"}, 400
        return {"error": "No file provided"}, 400


class WordListExport(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def get(self):
        source_ids = request.args.getlist("ids")
        data = word_list.WordList.export(source_ids)
        if data is None:
            return {"error": "Unable to export"}, 400
        return send_file(
            io.BytesIO(data),
            download_name="word_list_export.json",
            mimetype="application/json",
            as_attachment=True,
        )


class WordListGather(MethodView):
    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        return queue_manager.queue_manager.gather_word_list(word_list_id)


class WorkerInstances(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    def get(self):
        return queue_manager.queue_manager.ping_workers()


class Workers(MethodView):
    @auth_required("CONFIG_WORKER_ACCESS")
    @extract_args("search", "category", "type")
    def get(self, filter_args=None):
        return worker.Worker.get_all_for_api(filter_args, True)

    @auth_required("CONFIG_WORKER_ACCESS")
    def patch(self, worker_id):
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
    config_bp.add_url_rule("/publishers", view_func=Publishers.as_view("publishers"))
    config_bp.add_url_rule("/publishers-presets", view_func=PublisherPresets.as_view("publishers_presets"))
    config_bp.add_url_rule("/publishers-presets/<string:preset_id>", view_func=PublisherPresets.as_view("publishers_preset"))
    config_bp.add_url_rule("/publisher-presets", view_func=PublisherPresets.as_view("publisher_presets"))
    config_bp.add_url_rule("/publisher-presets/<string:preset_id>", view_func=PublisherPresets.as_view("publisher_preset"))

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
    config_bp.add_url_rule("/word-lists/<int:word_list_id>/gather", view_func=WordListGather.as_view("word_list_gather"))
    config_bp.add_url_rule("/export-word-lists", view_func=WordListExport.as_view("word_list_export"))
    config_bp.add_url_rule("/import-word-lists", view_func=WordListImport.as_view("word_list_import"))
    config_bp.add_url_rule("/workers", view_func=WorkerInstances.as_view("workers"))
    config_bp.add_url_rule("/workers/schedule", view_func=Schedule.as_view("queue_schedule_config"))
    config_bp.add_url_rule("/workers/tasks", view_func=QueueTasks.as_view("queue_tasks"))
    config_bp.add_url_rule("/workers/queue-status", view_func=QueueStatus.as_view("queue_status"))
    config_bp.add_url_rule("/schedule", view_func=Schedule.as_view("queue_schedule"))
    config_bp.add_url_rule("/schedule/<string:task_id>", view_func=Schedule.as_view("queue_schedule_task"))
    config_bp.add_url_rule("/worker-types", view_func=Workers.as_view("worker_types"))
    config_bp.add_url_rule("/worker-types/<string:worker_id>", view_func=Workers.as_view("worker_type_patch"))
    config_bp.add_url_rule("/refresh-interval", view_func=RefreshInterval.as_view("refresh_interval"))
    config_bp.add_url_rule("/connectors", view_func=Connectors.as_view("connectors"))
    config_bp.add_url_rule("/connectors/<string:connector_id>", view_func=Connectors.as_view("connector"))
    config_bp.add_url_rule("/connectors/<string:connector_id>/pull", view_func=ConnectorsPull.as_view("connector_collect"))

    app.register_blueprint(config_bp)
