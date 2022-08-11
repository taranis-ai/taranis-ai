import datetime

from bots.managers import time_manager
from bots.managers.log_manager import logger
from shared.schema import bot, bot_preset
from shared.schema.parameter import Parameter, ParameterType
from bots.remote.core_api import CoreApi


class BaseBot:
    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    parameters = [
        Parameter(
            0,
            "REFRESH_INTERVAL",
            "Refresh Interval",
            "How often is this bot doing its job",
            ParameterType.NUMBER,
        )
    ]

    def __init__(self):
        self.core_api = CoreApi()
        response, code = self.core_api.get_bots_presets(self.type)
        logger.log_debug(f"response: {response} type: {self.type}")
        if code != 200 or response is None:
            return
        preset_schema = bot_preset.BotPresetSchemaBase(many=True)
        self.bot_presets = preset_schema.load(response)
        for preset in self.bot_presets:
            self.execute(preset)
            if interval := preset.parameter_values["REFRESH_INTERVAL"]:
                self.set_time_manager_interval(interval, preset)

    def get_info(self):
        info_schema = bot.BotSchema()
        return info_schema.dump(self)

    def execute(self, source):
        pass

    def execute_on_event(self, preset, event_type, data):
        pass

    def process_event(self, event_type, data):
        for preset in self.bot_presets:
            self.execute_on_event(preset, event_type, data)

    @staticmethod
    def print_exception(preset, error):
        logger.log_debug(f"Bot Preset ID: {preset.id}\tName: {preset.name}")
        logger.log_debug_trace(error)

    @staticmethod
    def history(interval):
        if interval[0].isdigit() and ":" in interval:
            limit = datetime.datetime.now() - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
        elif int(interval) > 60:
            hours = int(interval) // 60
            minutes = int(interval) - hours * 60
            limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)

        else:
            limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))

        limit = limit.strftime("%d.%m.%Y - %H:%M")
        return limit

    def set_time_manager_interval(self, interval, preset):
        if interval[0].isdigit() and ":" in interval:
            time_manager.schedule_job_every_day(interval, self.execute, preset)
        elif interval[0].isalpha():
            interval = interval.split(",")
            day = interval[0].strip()
            at = interval[1].strip()
            if day == "Monday":
                time_manager.schedule_job_on_monday(at, self.execute, preset)
            elif day == "Tuesday":
                time_manager.schedule_job_on_tuesday(at, self.execute, preset)
            elif day == "Wednesday":
                time_manager.schedule_job_on_wednesday(at, self.execute, preset)
            elif day == "Thursday":
                time_manager.schedule_job_on_thursday(at, self.execute, preset)
            elif day == "Friday":
                time_manager.schedule_job_on_friday(at, self.execute, preset)
            elif day == "Saturday":
                time_manager.schedule_job_on_saturday(at, self.execute, preset)
            else:
                time_manager.schedule_job_on_sunday(at, self.execute, preset)
        else:
            logger.log_debug(f"SETTING INTERVAL: {interval} FOR: {self.name}")
            time_manager.schedule_job_minutes(int(interval), self.execute, preset)
