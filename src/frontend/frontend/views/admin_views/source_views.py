import base64
import json
from typing import Any, ClassVar, Literal

from flask import render_template, request, url_for
from models.admin import AdminMenuBadges, OSINTSource
from models.task import Task
from models.types import COLLECTOR_TYPES
from pydantic import ValidationError
from requests import RequestException
from requests import Response as RequestsResponse
from werkzeug.exceptions import HTTPException

from frontend.auth import admin_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_source_parameter, render_truncated, render_worker_status
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.views.admin_views.admin_base_view import AdminBaseView


class SourceView(AdminBaseView):
    model = OSINTSource
    icon = "book-open"
    import_route = "admin.import_osint_sources"
    _index = 63

    collector_types: ClassVar[dict[str, dict[str, str]]] = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in COLLECTOR_TYPES
        if member is not COLLECTOR_TYPES.PPN_COLLECTOR or not Config.DISABLE_PPN_COLLECTOR
    }
    bulk_url_parameters: ClassVar[dict[str, str]] = {
        COLLECTOR_TYPES.RSS_COLLECTOR.value: "FEED_URL",
        COLLECTOR_TYPES.SIMPLE_WEB_COLLECTOR.value: "WEB_URL",
        COLLECTOR_TYPES.RT_COLLECTOR.value: "BASE_URL",
        COLLECTOR_TYPES.MISP_COLLECTOR.value: "URL",
    }

    @staticmethod
    def get_collection_period() -> Literal["day", "week", "month"]:
        period = request.args.get("period", "week")
        if period == "day":
            return "day"
        if period == "month":
            return "month"
        return "week"

    @classmethod
    def get_object_by_id(cls, object_id: str) -> OSINTSource | None:
        result = CoreApi().api_get(
            f"{cls.model._core_endpoint}/{object_id}",
            params={"period": cls.get_collection_period()},
        )
        return OSINTSource(**result) if isinstance(result, dict) else None

    @classmethod
    def get_form_action(cls, object_id: str = "0") -> str:
        action = super().get_form_action(object_id)
        return f"{action}?period={cls.get_collection_period()}"

    @classmethod
    def get_admin_menu_badge(cls) -> int:
        try:
            badges = DataPersistenceLayer().get_object(AdminMenuBadges)
            if not badges:
                return 0

            return int(getattr(badges, "osint_source", 0) or 0)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error retrieving source admin menu badge")

        return 0

    @classmethod
    def get_admin_menu_badge_route(cls) -> str:
        return url_for("admin.osint_sources", filter_manual="false", state="failure")

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}

        osint_source_actions = [
            {
                "label": "Preview",
                "icon": "eye",
                "method": "post",
                "url": url_for("admin.osint_source_preview", osint_source_id=""),
                "type": "link",
            },
            {
                "label": "Collect",
                "icon": "arrows-pointing-in",
                "method": "post",
                "url": url_for("admin.collect_osint_source", osint_source_id=""),
                "hx_target_error": "#notification-bar",
                "hx_target": "#notification-bar",
                "hx_swap": "outerHTML",
                "confirm": None,
            },
            {"label": "Edit", "class": "btn-primary", "icon": "pencil-square", "url": cls.get_base_route(), "type": "link"},
            {
                "label": "Delete",
                "icon": "trash",
                "class": "btn-error",
                "method": "delete",
                "url": cls.get_base_route(),
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
                "type": "button",
                "confirm": "Are you sure you want to delete this OSINT Source?",
                "data_attr": "data-force-delete",
            },
        ]

        collector = base_context.get(cls.model_name())
        if collector and (collector_type := collector.type):
            parameter_values = collector.parameters
            parameters = cls.get_worker_parameters(worker_type=collector_type.name.lower())

        base_context["parameters"] = parameters
        base_context["parameter_values"] = parameter_values
        base_context["worker_parameters_selected"] = bool(collector and collector.type)
        base_context["collector_types"] = cls.collector_types.values()
        base_context["icon_accept"] = Config.OSINT_SOURCE_ICON_ALLOWED_MIMETYPES
        base_context["actions"] = osint_source_actions
        base_context["secret_reveal_url"] = (
            f"{Config.TARANIS_BASE_PATH.rstrip('/')}/api/config/parameter-secrets/sources/{collector.id}"
            if collector and collector.id
            else ""
        )
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "State", "field": "status", "sortable": True, "renderer": render_worker_status},
            {
                "title": "Name",
                "field": "name",
                "sortable": True,
                "renderer": render_truncated,
                "render_args": {"field": "name"},
            },
            {"title": "Feed", "field": "parameters", "sortable": False, "renderer": render_source_parameter},
        ]

    @classmethod
    def get_osint_source_parameters_view(cls, osint_source_id: str, collector_type: str, *, bulk: bool = False):
        if not osint_source_id and not collector_type:
            logger.warning("No OSINT source ID or collector type provided.")

        parameters = cls.get_worker_parameters(collector_type)
        if bulk and (url_parameter := cls.bulk_url_parameters.get(collector_type)):
            parameters = [parameter for parameter in parameters if parameter["name"] != url_parameter]

        return render_template("partials/worker_parameters.html", parameters=parameters, worker_parameters_selected=True)

    @classmethod
    def get_bulk_create_context(cls, form_data: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
        form_data = form_data or {}
        collector_type = str(form_data.get("type") or "")
        parameters = cls.get_worker_parameters(collector_type) if collector_type in cls.bulk_url_parameters else []
        if url_parameter := cls.bulk_url_parameters.get(collector_type):
            parameters = [parameter for parameter in parameters if parameter["name"] != url_parameter]

        sources = form_data.get("sources") or [{"name": "", "url": ""}, {"name": "", "url": ""}]
        if isinstance(sources, dict):
            sources = list(sources.values())

        return {
            "collector_types": [cls.collector_types[supported_type] for supported_type in cls.bulk_url_parameters],
            "create_group": str(form_data.get("create_group", "false")).lower() in {"true", "1", "yes", "on"},
            "description": form_data.get("description", ""),
            "error": error,
            "form_action": url_for("admin.bulk_create_osint_sources"),
            "group_description": form_data.get("group_description", ""),
            "group_name": form_data.get("group_name", ""),
            "icon_accept": Config.OSINT_SOURCE_ICON_ALLOWED_MIMETYPES,
            "parameters": parameters,
            "parameter_values": form_data.get("parameters", {}),
            "worker_parameters_selected": bool(collector_type),
            "rank": form_data.get("rank", 0),
            "selected_collector_type": collector_type,
            "sources": sources,
        }

    @classmethod
    def bulk_create_view(cls):
        return render_template("osint_source/osint_source_bulk_create.html", **cls.get_bulk_create_context())

    @classmethod
    def bulk_create_post_view(cls):
        form_data = parse_formdata(request.form)
        sources = form_data.get("sources", [])
        if isinstance(sources, dict):
            sources = list(sources.values())
        if not isinstance(sources, list) or len(sources) < 2:
            return cls._render_bulk_create_error(form_data, "Add at least two OSINT sources.")

        collector_type = str(form_data.get("type") or "")
        if not (url_parameter := cls.bulk_url_parameters.get(collector_type)):
            return cls._render_bulk_create_error(form_data, "Select a supported collector type.")

        normalized_sources = []
        for source in sources:
            if not isinstance(source, dict):
                return cls._render_bulk_create_error(form_data, "Each OSINT source needs a name and source URL.")
            name = str(source.get("name") or "").strip()
            url = str(source.get("url") or "").strip()
            if not name or not url:
                return cls._render_bulk_create_error(form_data, "Each OSINT source needs a name and source URL.")
            normalized_sources.append({"name": name, "url": url})

        create_group = str(form_data.get("create_group", "false")).lower() in {"true", "1", "yes", "on"}
        group_name = str(form_data.get("group_name") or "").strip()
        if create_group and not group_name:
            return cls._render_bulk_create_error(form_data, "Enter a name for the OSINT source group.")

        icon_value = None
        if (icon := request.files.get("icon")) and icon.filename:
            max_bytes = Config.OSINT_SOURCE_ICON_MAX_BYTES
            icon_data = icon.read(max_bytes + 1)
            if len(icon_data) > max_bytes:
                return cls._render_bulk_create_error(form_data, f"Icon file exceeds maximum size of {max_bytes} bytes.")
            icon_value = base64.b64encode(icon_data).decode("utf-8")

        shared_parameters = form_data.get("parameters", {})
        if not isinstance(shared_parameters, dict):
            return cls._render_bulk_create_error(form_data, "Invalid shared source settings.")

        import_sources = []
        source_indexes = []
        for index, source in enumerate(normalized_sources, 1):
            source_data = {
                "name": source["name"],
                "description": form_data.get("description", ""),
                "rank": form_data.get("rank", 0),
                "type": collector_type,
                "parameters": {**shared_parameters, url_parameter: source["url"]},
            }
            if icon_value is not None:
                source_data["icon"] = icon_value
            if create_group:
                source_data["group_idx"] = index
                source_indexes.append(index)
            import_sources.append(source_data)

        groups = []
        if create_group:
            groups.append(
                {
                    "name": group_name,
                    "description": form_data.get("group_description", ""),
                    "osint_sources": source_indexes,
                }
            )

        try:
            response = CoreApi().import_sources({"version": 4, "sources": import_sources, "groups": groups})
        except RequestException:
            logger.exception("Bulk OSINT source creation request failed")
            return cls._render_bulk_create_error(form_data, "Failed to create OSINT sources.", 502)

        if response is None or not response.ok:
            payload = cls._response_payload(response)
            error = payload.get("error") if payload else None
            if not isinstance(error, str) or not error:
                error = "Failed to create OSINT sources."
            status = response.status_code if response is not None else 502
            return cls._render_bulk_create_error(form_data, error, status)

        message = f"Successfully created {len(import_sources)} OSINT sources"
        if create_group:
            message += " and their source group"
        cls.add_flash_notification({"message": f"{message}."})
        return cls.redirect_htmx(cls.get_base_route())

    @classmethod
    def _render_bulk_create_error(cls, form_data: dict[str, Any], error: str, status: int = 400) -> tuple[str, int]:
        logger.warning(f"Bulk OSINT source creation failed: {error}")
        return render_template(
            "osint_source/osint_source_bulk_create.html",
            **cls.get_bulk_create_context(form_data, error),
        ), status

    @classmethod
    def import_view(cls, error: str | None = None):
        return render_template(f"{cls.model_name().lower()}/{cls.model_name().lower()}_import.html", error=error)

    @classmethod
    def import_post_view(cls):
        sources = request.files.get("file")
        if not sources:
            return cls.import_view("No file or organization provided")
        data = sources.read()
        json_data = json.loads(data)

        response = CoreApi().import_sources(json_data)

        if not response:
            error = "Failed to import sources"
            return cls.import_view(error)

        cls.add_flash_notification(response)
        return cls.redirect_htmx(cls.get_base_route())

    @classmethod
    def get_submit_redirect_target(cls, object_id: str, core_response: dict[str, Any]) -> str:
        target_id = core_response.get("id") or object_id
        if cls.is_create_object_id(target_id):
            return cls.get_base_route()
        return cls.get_edit_route(**{cls._get_object_key(): target_id}, period=cls.get_collection_period())

    @classmethod
    def process_form_data(cls, object_id: str):
        try:
            form_data = parse_formdata(request.form)
            delete_icon = str(form_data.pop("delete_icon", "")).lower() in {"true", "1", "yes", "on"}

            if delete_icon:
                # Explicit delete must win over any concurrent file upload.
                form_data["icon"] = ""
            else:
                icon = request.files.get("icon")  # FileStorage
                if icon and icon.filename:
                    max_bytes = Config.OSINT_SOURCE_ICON_MAX_BYTES
                    icon_data = icon.read(max_bytes + 1)
                    if len(icon_data) > max_bytes:
                        error_msg = f"Icon file exceeds maximum size of {max_bytes} bytes."
                        logger.warning(error_msg)
                        return None, error_msg

                    icon_data_base64 = base64.b64encode(icon_data).decode("utf-8")
                    form_data["icon"] = icon_data_base64

            core_response, error = cls.store_form_data(form_data, object_id)
            return core_response, cls._extract_error_message(error)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error storing form data")
            return None, "Error storing form data"

    @staticmethod
    def _extract_error_message(error: Any) -> Any:
        if isinstance(error, dict):
            return error.get("error", str(error))
        return error

    @classmethod
    def export_view(cls):
        source_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_sources({"ids": source_ids})

        if not core_resp:
            logger.debug(f"Failed to fetch sources from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch sources from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "sources_export.json")

    @classmethod
    def load_default_osint_sources(cls):
        dpl = DataPersistenceLayer()
        response = CoreApi().load_default_osint_sources()
        if not response:
            logger.error("Failed to load default OSINT sources")
            return render_template("notification/index.html", notification={"message": "Failed to load default OSINT sources", "error": True})

        response = CoreApi().import_sources(response)

        if not response.ok:
            error = response.json().get("error", "Unknown error")
            error_message = f"Failed to import default OSINT sources: {error}"
            logger.error(error_message)
            return render_template("notification/index.html", notification={"message": error_message, "error": True})

        dpl.invalidate_cache_by_object(cls.model)
        dpl.invalidate_model_cache_locally(cls.model)
        items = dpl.get_objects(cls.model)
        return render_template(cls.get_list_template(), **cls.get_view_context(items))

    @classmethod
    def _collect_source_view(cls, response: RequestsResponse | None):
        if response is None:
            logger.error("Failed to start OSINT source collection")
        status = response.status_code if response is not None else 500
        notification = cls.render_worker_task_notification(response)

        table, table_response = cls.render_list()
        status = table_response if table_response != 200 else status
        return notification + table, status

    @classmethod
    def collect_osint_source(cls, osint_source_id: str):
        response = CoreApi().collect_osint_source(osint_source_id)
        return cls._collect_source_view(response)

    @classmethod
    def collect_all_osint_sources(cls):
        response = CoreApi().collect_all_osint_sources()
        return cls._collect_source_view(response)

    @classmethod
    @admin_required()
    def get_osint_source_preview_view(cls, osint_source_id: str):
        task_result = None
        response = CoreApi().get_osint_source_preview(osint_source_id)
        if isinstance(response, dict):
            task_result = Task.model_validate(response)
        return render_template("osint_source/osint_source_preview.html", task_result=task_result, osint_source_id=osint_source_id)

    @classmethod
    @admin_required()
    def retrigger_osint_source_preview_view(cls, osint_source_id: str):
        task_result = None
        response = CoreApi().retrigger_osint_source_preview(osint_source_id)
        if isinstance(response, dict):
            task_result = Task.model_validate(response)
        return render_template("osint_source/osint_source_preview.html", task_result=task_result, osint_source_id=osint_source_id)

    @classmethod
    def delete_view(cls, object_id: str) -> tuple[str, int]:
        force = request.values.get("force") == "true"
        dpl = DataPersistenceLayer()
        params = {"force": "true"} if force else None
        core_response = dpl.delete_object(cls.model, object_id, params=params)

        response = cls.get_notification_from_response(core_response)
        if not core_response.ok:
            return response, core_response.status_code or 500

        cls._invalidate_model_cache(object_id)
        if force:
            logger.debug(f"Force deleted OSINT source {object_id}")

        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code or table_response

    @classmethod
    def delete_multiple_view(cls, object_ids: list[str]) -> tuple[str, int]:
        force = request.values.get("force") == "true"
        params: dict[str, Any] = {"ids": object_ids}
        if force:
            params["force"] = "true"

        core_response = CoreApi().api_delete(cls.model._core_endpoint, params=params)
        if not core_response.ok:
            return cls.get_notification_from_response(core_response), core_response.status_code or 500

        cls._invalidate_model_cache()
        response, status_code = cls.render_list()
        response += render_template(
            "notification/index.html", notification={"message": "Selected items deleted successfully", "error": False}
        )
        return response, status_code

    @classmethod
    @admin_required()
    def toggle_osint_source_state(cls, osint_source_id: str, new_state: Literal["enabled", "disabled"]) -> tuple[str, int]:
        dpl = DataPersistenceLayer()

        response = CoreApi().toggle_osint_source(osint_source_id, new_state)
        if not response:
            logger.error(f"Failed to toggle OSINT source state for {osint_source_id}")
            return render_template(
                "notification/index.html", notification={"message": "Failed to toggle OSINT source state", "error": True}
            ), 500

        notification = render_template(
            "notification/index.html",
            notification={"message": "OSINT source state updated successfully", "icon": "check-circle", "class": "alert-success"},
        )
        osint_source = dpl.get_object(OSINTSource, osint_source_id)
        state_button = render_template("osint_source/state_button.html", osint_source=osint_source)

        return notification + state_button, 200
