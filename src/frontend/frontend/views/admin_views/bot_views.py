from typing import Any
from flask import render_template, url_for, request

from frontend.views.base_view import BaseView
from frontend.log import logger
from models.admin import Bot
from models.types import BOT_TYPES
from frontend.core_api import CoreApi
from frontend.auth import auth_required
from frontend.filters import render_item_type, render_worker_status
from frontend.data_persistence import DataPersistenceLayer
from models.dashboard import Dashboard
from frontend.views.admin_views.admin_mixin import AdminMixin


class BotView(AdminMixin, BaseView):
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
        ]

    @classmethod
    def get_admin_menu_badge(cls) -> int:
        if dashboard := DataPersistenceLayer().get_first(Dashboard):
            if worker_status := dashboard.worker_status:
                return worker_status.get("bot_task", {}).get("failures", 0)

        return 0

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
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
        if bot and (hasattr(bot, "type") and (bot_type := bot.type)):
            parameter_values = bot.parameters
            parameters = cls.get_worker_parameters(bot_type.name.lower())

        base_context |= {
            "bot_types": cls.bot_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
            "actions": bot_actions + cls.get_default_actions(),
        }
        return base_context

    @classmethod
    @auth_required()
    def get_bot_parameters_view(cls, bot_id: str):
        bot_type = request.args.get("type", "")
        if not bot_id and not bot_type:
            logger.warning("No bot ID or bot type provided.")

        parameters = cls.get_worker_parameters(bot_type)

        return render_template("partials/worker_parameters.html", parameters=parameters)

    @classmethod
    @auth_required()
    def execute_bot(cls, bot_id: str):
        response = CoreApi().execute_bot(bot_id)
        if not response:
            logger.error("Failed to execute bot.")
            return render_template("notification/index.html", notification={"message": "Failed to execute bot.", "error": True}), 500
        return render_template(
            "notification/index.html", notification={"message": "Bot executed successfully", "class": "alert-success"}
        ), 200
