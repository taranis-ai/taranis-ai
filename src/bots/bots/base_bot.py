import datetime

from managers import time_manager
from schema import bot, bot_preset
from schema.parameter import Parameter, ParameterType
from remote.core_api import CoreApi


class BaseBot:
    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    parameters = [
        Parameter(0, "REFRESH_INTERVAL", "Refresh Interval", "How often is this bot doing its job",
                  ParameterType.NUMBER)
    ]

    def __init__(self):
        self.bot_presets = []

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
        print('Bot Preset ID: ' + preset.id)
        print('Bot Preset name: ' + preset.name)
        if str(error).startswith('b'):
            print('ERROR: ' + str(error)[2:-1])
        else:
            print('ERROR: ' + str(error))

    @staticmethod
    def history(interval):
        if interval[0].isdigit() and ':' in interval:
            limit = datetime.datetime.now() - datetime.timedelta(days=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        elif interval[0].isalpha():
            limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
            limit = limit.strftime("%d.%m.%Y - %H:%M")
        else:
            if int(interval) > 60:
                hours = int(interval) // 60
                minutes = int(interval) - hours * 60
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)
                limit = limit.strftime("%d.%m.%Y - %H:%M")
            else:
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))
                limit = limit.strftime("%d.%m.%Y - %H:%M")

        return limit

    def initialize(self):
        response, code = CoreApi.get_bots_presets(self.type)
        if code == 200 and response is not None:
            preset_schema = bot_preset.BotPresetSchemaBase(many=True)
            self.bot_presets = preset_schema.load(response)

            for preset in self.bot_presets:
                self.execute(preset)
                interval = preset.parameter_values["REFRESH_INTERVAL"]

                if interval:
                    if interval[0].isdigit() and ':' in interval:
                        time_manager.schedule_job_every_day(interval, self.execute, preset)
                    elif interval[0].isalpha():
                        interval = interval.split(',')
                        day = interval[0].strip()
                        at = interval[1].strip()
                        if day == 'Monday':
                            time_manager.schedule_job_on_monday(at, self.execute, preset)
                        elif day == 'Tuesday':
                            time_manager.schedule_job_on_tuesday(at, self.execute, preset)
                        elif day == 'Wednesday':
                            time_manager.schedule_job_on_wednesday(at, self.execute, preset)
                        elif day == 'Thursday':
                            time_manager.schedule_job_on_thursday(at, self.execute, preset)
                        elif day == 'Friday':
                            time_manager.schedule_job_on_friday(at, self.execute, preset)
                        elif day == 'Saturday':
                            time_manager.schedule_job_on_saturday(at, self.execute, preset)
                        else:
                            time_manager.schedule_job_on_sunday(at, self.execute, preset)
                    else:
                        time_manager.schedule_job_minutes(int(interval), self.execute, preset)
