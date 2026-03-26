from typing import Any

from flask import render_template, request, url_for
from models.admin import Bot
from models.dashboard import Dashboard
from models.types import BOT_TYPES

from frontend.auth import admin_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_item_type, render_worker_status
from frontend.log import logger
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


BOT_PARAMETER_ORDER_BY_TYPE = {
    "analyst_bot": ["REGULAR_EXPRESSION", "ATTRIBUTE_NAME", "ITEM_FILTER", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "grouping_bot": ["REGULAR_EXPRESSION", "ITEM_FILTER", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "nlp_bot": ["ITEM_FILTER", "REQUESTS_TIMEOUT", "BOT_ENDPOINT", "BOT_API_KEY", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "ioc_bot": ["ITEM_FILTER", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "tagging_bot": ["KEYWORDS", "ITEM_FILTER", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "story_bot": ["ITEM_FILTER", "REQUESTS_TIMEOUT", "BOT_ENDPOINT", "BOT_API_KEY", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "summary_bot": ["ITEM_FILTER", "REQUESTS_TIMEOUT", "BOT_ENDPOINT", "BOT_API_KEY", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "wordlist_bot": ["ITEM_FILTER", "TAGGING_WORDLISTS", "RUN_AFTER_COLLECTOR", "REFRESH_INTERVAL"],
    "sentiment_analysis_bot": [
        "ITEM_FILTER",
        "REQUESTS_TIMEOUT",
        "BOT_ENDPOINT",
        "BOT_API_KEY",
        "RUN_AFTER_COLLECTOR",
        "REFRESH_INTERVAL",
    ],
    "cybersec_classifier_bot": [
        "ITEM_FILTER",
        "REQUESTS_TIMEOUT",
        "BOT_ENDPOINT",
        "BOT_API_KEY",
        "CLASSIFICATION_THRESHOLD",
        "RUN_AFTER_COLLECTOR",
        "REFRESH_INTERVAL",
    ],
}
OPTIONAL_BOT_PARAMETERS = {"REFRESH_INTERVAL"}


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
        try:
            if dashboard := DataPersistenceLayer().get_first(Dashboard):
                if worker_status := dashboard.worker_status:
                    return worker_status.get("bot_task", {}).get("failures", 0)
        except Exception:
            logger.exception("Error retrieving dashboard for bot admin menu badge")

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
            bot_type_name = bot_type.name.lower()
            parameters = cls._reorder_bot_parameters(bot_type_name, cls.get_worker_parameters(bot_type_name))

        base_context |= {
            "bot_types": cls.bot_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
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

        parameters = cls._reorder_bot_parameters(bot_type, cls.get_worker_parameters(bot_type))

        return render_template(
            "partials/worker_parameters.html",
            parameters=parameters,
            optional_parameters=OPTIONAL_BOT_PARAMETERS,
        )

    @staticmethod
    def _reorder_bot_parameters(bot_type: str, parameters: list[Any]) -> list[Any]:
        order_index = {name: idx for idx, name in enumerate(BOT_PARAMETER_ORDER_BY_TYPE.get(bot_type, []))}

        def get_parameter_name(parameter: Any) -> Any:
            if isinstance(parameter, dict):
                return parameter.get("name")
            return getattr(parameter, "name", None)

        ordered_parameters = sorted(
            enumerate(parameters),
            key=lambda entry: (order_index.get(get_parameter_name(entry[1]), float("inf")), entry[0]),
        )
        return [parameter for _, parameter in ordered_parameters]

    @classmethod
    @admin_required()
    def execute_bot(cls, bot_id: str):
        response = CoreApi().execute_bot(bot_id)
        if not response:
            logger.error("Failed to execute bot.")
            return render_template("notification/index.html", notification={"message": "Failed to execute bot.", "error": True}), 500
        return render_template(
            "notification/index.html", notification={"message": "Bot executed successfully", "class": "alert-success"}
        ), 200
