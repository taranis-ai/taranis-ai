from typing import Any
from flask import render_template, url_for

from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from models.admin import Bot, WorkerParameter, WorkerParameterValue
from models.types import BOT_TYPES
from frontend.core_api import CoreApi


class BotView(BaseView):
    model = Bot
    icon = "calculator"
    _index = 110

    bot_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in BOT_TYPES
    }

    @classmethod
    def get_worker_parameters(cls, bot_type: str) -> list[WorkerParameterValue]:
        dpl = DataPersistenceLayer()
        all_parameters = dpl.get_objects(WorkerParameter)
        match = next((wp for wp in all_parameters if wp.id == bot_type), None)
        return match.parameters if match else []

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}

        bot_actions = [
            {
                "label": "Run Bot",
                "class": "",
                "icon": "rocket-launch",
                "method": "post",
                "url": url_for("admin.execute_bot", bot_id=""),
                "hx_target_error": "#error-msg",
                "hx_target": "#notification-bar",
                "hx_swap": "outerHTML",
                "confirm": None,
            },
        ]

        bot = base_context.get(cls.model_name())
        if bot and (bot_type := bot.type):
            parameter_values = bot.parameters
            parameters = cls.get_worker_parameters(bot_type=bot_type.name.lower())

        base_context |= {
            "bot_types": cls.bot_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
            "actions": bot_actions + cls.get_default_actions(),
        }
        return base_context

    @classmethod
    def get_bot_parameters_view(cls, bot_id: str, bot_type: str):
        if not bot_id and not bot_type:
            logger.warning("No bot ID or bot type provided.")

        parameters = cls.get_worker_parameters(bot_type)

        return render_template("partials/worker_parameters.html", parameters=parameters)

    @classmethod
    def execute_bot(cls, bot_id: str):
        response = CoreApi().execute_bot(bot_id)
        logger.debug(f"Execute bot response: {response}")
        if not response:
            logger.error("Failed to execute bot.")
            return render_template("partials/error.html", error="Failed to execute bot."), 500
        return render_template("notification/index.html", notification="Bot executed successfully"), 200
