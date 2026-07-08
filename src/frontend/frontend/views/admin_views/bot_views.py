from typing import Any

from flask import render_template, request, url_for
from markupsafe import Markup, escape
from models.admin import AdminMenuBadges, Bot
from models.types import BOT_TYPES
from werkzeug.exceptions import HTTPException

from frontend.auth import admin_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_item_type, render_worker_status
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


OPTIONAL_BOT_PARAMETERS = {"REFRESH_INTERVAL"}
RUN_ORDER_PARAMETERS = {"RUN_AFTER_COLLECTOR", "RUN_AFTER_BOTS"}


def render_bot_run_order(item: Bot) -> Markup:
    parameters = item.parameters or {}
    parts = []
    if parameters.get("RUN_AFTER_COLLECTOR") == "true":
        parts.append('<span class="badge badge-primary badge-sm">Collector</span>')
    for bot_type in _split_run_after_bots(parameters.get("RUN_AFTER_BOTS", "")):
        parts.append(f'<span class="badge badge-outline badge-sm">{escape(bot_type)}</span>')
    return Markup('<div class="flex flex-wrap gap-1">' + "".join(parts or ['<span class="text-base-content/50">Manual</span>']) + "</div>")


def _split_run_after_bots(value: Any) -> list[str]:
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").split(",")
    return [str(item).strip() for item in values if str(item).strip()]


class BotView(AdminBaseView):
    model = Bot
    icon = "calculator"
    _index = 110

    bot_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in BOT_TYPES
    }

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Status", "field": "status", "sortable": True, "renderer": render_worker_status},
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
            {"title": "Run Order", "field": "parameters", "sortable": False, "renderer": render_bot_run_order},
        ]

    @classmethod
    def get_admin_menu_badge(cls) -> int:
        try:
            badges = DataPersistenceLayer().get_object(AdminMenuBadges)
            if not badges:
                return 0

            return int(getattr(badges, "bot", 0) or 0)
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error retrieving bot admin menu badge")

        return 0

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}

        bot_actions = [
            {
                "label": "Run Bot",
                "icon": "rocket-launch",
                "method": "post",
                "url": url_for("admin.execute_bot", bot_id=""),
                "hx_target": "#notification-bar",
                "hx_swap": "outerHTML",
            },
        ]

        bot = base_context.get(cls.model_name())
        bot_type_name = request.args.get("type", "")
        if bot and (hasattr(bot, "type") and (bot_type := bot.type)):
            parameter_values = bot.parameters
            bot_type_name = bot_type.name.lower()
            parameters = cls._filter_run_order_parameters(cls.get_worker_parameters(bot_type_name))

        base_context |= {
            "bot_types": cls.get_bot_type_options(bot),
            "parameter_values": parameter_values,
            "parameters": parameters,
            "run_after_options": cls.get_run_after_options(bot_type_name),
            "selected_run_after": _split_run_after_bots(parameter_values.get("RUN_AFTER_BOTS", "")),
            "dag_preview": cls.get_dag_preview(base_context.get("bot_id", "0"), bot.model_dump(mode="json") if bot else {}),
            "optional_parameters": OPTIONAL_BOT_PARAMETERS,
            "actions": bot_actions + cls.get_default_actions(),
        }
        return base_context

    @classmethod
    @admin_required()
    def get_bot_parameters_view(cls, bot_id: str):
        bot_type = request.args.get("type", "")
        if not bot_id and not bot_type:
            logger.warning("No bot ID or bot type provided.")

        parameters = cls._filter_run_order_parameters(cls.get_worker_parameters(bot_type))

        return render_template(
            "bot/bot_config_fields.html",
            parameters=parameters,
            parameter_values={},
            run_after_options=cls.get_run_after_options(bot_type),
            selected_run_after=[],
            bot_id=bot_id,
            dag_preview=cls.get_dag_preview(bot_id, {"type": bot_type} if bot_type else {}),
            optional_parameters=OPTIONAL_BOT_PARAMETERS,
        )

    @classmethod
    @admin_required()
    def execute_bot(cls, bot_id: str):
        response = CoreApi().execute_bot(bot_id)
        if response is None:
            logger.error("Failed to execute bot.")
        status = response.status_code if response is not None else 500
        return cls.render_worker_task_notification(response), status

    @classmethod
    @admin_required()
    def preview_bot_dag(cls, bot_id: str):
        payload = cls._get_normalized_form_data()
        parameters = payload.get("parameters") or {}
        return (
            render_template(
                "bot/bot_dag_preview.html",
                bot_id=bot_id,
                dag_preview=cls.get_dag_preview(bot_id, payload),
                run_after_collector=parameters.get("RUN_AFTER_COLLECTOR") == "true",
            ),
            200,
        )

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        parameters = dict(form_data.get("parameters") or {})
        parameters["RUN_AFTER_COLLECTOR"] = parameters.get("RUN_AFTER_COLLECTOR", "false")
        parameters["RUN_AFTER_BOTS"] = ",".join(_split_run_after_bots(parameters.get("RUN_AFTER_BOTS", "")))
        form_data["parameters"] = parameters
        return form_data

    @classmethod
    def _filter_run_order_parameters(cls, parameters: list[Any]) -> list[Any]:
        return [parameter for parameter in parameters if parameter.name not in RUN_ORDER_PARAMETERS]

    @classmethod
    def get_bot_type_options(cls, current_bot: Bot | None = None) -> list[dict[str, str]]:
        current_type = current_bot.type.name.lower() if current_bot and current_bot.type else ""
        used_types = cls._used_bot_type_names(exclude_type=current_type)
        return [option for option in cls.bot_types.values() if option["id"] == current_type or option["id"] not in used_types]

    @classmethod
    def get_run_after_options(cls, current_type: str = "") -> list[dict[str, str]]:
        current_type = current_type.lower()
        try:
            bots = DataPersistenceLayer().get_objects(Bot).items
        except Exception:
            logger.exception("Failed to load bot run order options")
            bots = []
        return [
            {
                "id": bot.type.name,
                "name": f"{bot.name} ({bot.type.name})",
                "enabled": "true" if bot.enabled else "false",
            }
            for bot in bots
            if bot.type.name.lower() != current_type
        ]

    @classmethod
    def get_dag_preview(cls, bot_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = CoreApi().preview_bot_dag(bot_id, payload)
        if response is not None and response.ok:
            return response.json()
        return {"order": [], "edges": [], "nodes": [], "warnings": ["Run order preview is unavailable"]}

    @classmethod
    def _used_bot_type_names(cls, exclude_type: str = "") -> set[str]:
        try:
            bots = DataPersistenceLayer().get_objects(Bot).items
        except Exception:
            return set()
        return {bot.type.name.lower() for bot in bots if bot.type.name.lower() != exclude_type}
