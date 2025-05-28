from typing import Any
from flask import render_template

from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from models.admin import Bot, WorkerParameter, WorkerParameterValue
from models.types import BOT_TYPES


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
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        parameters = {}
        parameter_values = {}
        if str(object_id) != "0" and object_id:
            if bot := dpl.get_object(Bot, object_id):
                if bot_type := bot.type:
                    parameter_values = bot.parameters
                    parameters = cls.get_worker_parameters(bot_type=bot_type.name.lower())

        return {
            "bot_types": cls.bot_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
        }

    @classmethod
    def get_bot_parameters_view(cls, bot_id: str, bot_type: str):
        if not bot_id and not bot_type:
            logger.warning("No bot ID or bot type provided.")

        parameters = cls.get_worker_parameters(bot_type)
        logger.debug(f"Parameters for bot type '{bot_type}': {parameters}")

        return render_template("partials/worker_parameters.html", parameters=parameters)
