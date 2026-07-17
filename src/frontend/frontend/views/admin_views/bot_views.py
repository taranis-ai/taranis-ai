from typing import Any, Literal

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


def render_bot_run_order(item: Bot, bot_names: dict[str, str]) -> Markup:
    parameters = item.parameters or {}
    parts = []
    if parameters.get("RUN_AFTER_COLLECTOR") == "true":
        parts.append('<span class="badge badge-primary badge-sm">Collector</span>')
    for bot_id in _split_run_after_bots(parameters.get("RUN_AFTER_BOTS", "")):
        parts.append(f'<span class="badge badge-outline badge-sm">{escape(bot_names.get(bot_id, bot_id))}</span>')
    return Markup('<div class="flex flex-wrap gap-1">' + "".join(parts or ['<span class="text-base-content/50">Manual</span>']) + "</div>")


def _split_run_after_bots(value: Any) -> list[str]:
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").split(",")
    return [str(item).strip() for item in values if str(item).strip()]


def _bot_type_name(item: Bot | None) -> str:
    bot_type = getattr(item, "type", None)
    return bot_type.name if bot_type else ""


def _bot_names_by_id() -> dict[str, str]:
    try:
        return {bot.id: bot.name for bot in DataPersistenceLayer().get_objects(Bot).items if bot.id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to load bot instance names")
        return {}


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
        bot_names = _bot_names_by_id()
        return [
            {"title": "Status", "field": "status", "sortable": True, "renderer": render_worker_status},
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
            {
                "title": "Run Order",
                "field": "parameters",
                "sortable": False,
                "renderer": render_bot_run_order,
                "render_args": {"bot_names": bot_names},
            },
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
        dag_preview = {"order": [], "edges": [], "nodes": [], "warnings": []}

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
        if bot and (bot_type := _bot_type_name(bot)):
            parameter_values = bot.parameters or {}
            bot_type_name = bot_type.lower()
            parameters = cls._filter_run_order_parameters(cls.get_worker_parameters(bot_type_name))
            dag_preview = cls.get_dag_preview(
                {
                    "id": bot.id,
                    "type": bot_type,
                    "index": bot.index,
                    "enabled": bot.enabled,
                    "parameters": {key: parameter_values.get(key, "") for key in RUN_ORDER_PARAMETERS},
                }
            )

        base_context |= {
            "bot_types": cls.bot_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
            "run_after_options": cls.get_run_after_options(bot.id if bot else ""),
            "selected_run_after": _split_run_after_bots(parameter_values.get("RUN_AFTER_BOTS", "")),
            "dag_preview": dag_preview,
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
            run_after_options=cls.get_run_after_options("" if bot_id == "0" else bot_id),
            selected_run_after=[],
            bot_id=bot_id,
            dag_preview=cls.get_dag_preview({"type": bot_type}) if bot_type else {"order": [], "edges": [], "nodes": [], "warnings": []},
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
    def preview_bot_dag(cls):
        form_data = cls._get_normalized_form_data()
        parameters = form_data.get("parameters") or {}
        payload = {key: form_data[key] for key in ("id", "type", "index", "enabled") if key in form_data}
        payload["parameters"] = {key: parameters[key] for key in RUN_ORDER_PARAMETERS if key in parameters}
        return (
            render_template(
                "bot/bot_dag_preview.html",
                dag_preview=cls.get_dag_preview(payload),
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
    def get_run_after_options(cls, current_bot_id: str = "") -> list[dict[str, str]]:
        try:
            bots = DataPersistenceLayer().get_objects(Bot).items
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to load bot run order options")
            bots = []
        return [
            {
                "id": bot.id,
                "name": f"{bot.name} ({_bot_type_name(bot)})",
                "enabled": "true" if bot.enabled else "false",
            }
            for bot in bots
            if bot.id and bot.id != current_bot_id
        ]

    @classmethod
    def get_dag_preview(cls, payload: dict[str, Any]) -> dict[str, Any]:
        response = CoreApi().preview_bot_dag(payload)
        if response is not None and response.ok:
            return response.json()
        return {"order": [], "edges": [], "nodes": [], "warnings": ["Run order preview is unavailable"]}

    @classmethod
    @admin_required()
    def toggle_bot_state(cls, bot_id: str, new_state: Literal["enabled", "disabled"]) -> tuple[str, int]:
        dpl = DataPersistenceLayer()

        response = CoreApi().toggle_bot(bot_id, new_state)
        if not response:
            logger.error(f"Failed to toggle bot state for {bot_id}")
            return render_template("notification/index.html", notification={"message": "Failed to toggle bot state", "error": True}), 500

        dpl.invalidate_cache_by_object(Bot)
        dpl.invalidate_model_cache_locally(Bot, bot_id)
        bot = dpl.get_object(Bot, bot_id)
        if bot is None:
            logger.error(f"Bot {bot_id} not found after state toggle")
            return render_template("notification/index.html", notification={"message": "Failed to refresh bot state", "error": True}), 500

        notification = render_template(
            "notification/index.html",
            notification={"message": "Bot state updated successfully", "icon": "check-circle", "class": "alert-success"},
        )
        state_button = render_template("bot/state_button.html", bot=bot)

        return notification + state_button, 200
