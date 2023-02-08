import datetime

from bots.managers.log_manager import logger
from shared.schema.bot import BotSchema
from bots.remote.core_api import CoreApi


class BaseBot:
    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    def __init__(self, parameters: dict):
        self.core_api = CoreApi()
        self.parameters = parameters
        self.bot_setup()
        self.refresh()

    def bot_setup(self):
        pass

    def get_info(self):
        info_schema = BotSchema()
        return info_schema.dump(self)

    def execute(self):
        pass

    def execute_on_event(self, event_type, data):
        pass

    def history(self):
        interval = self.parameters.get("REFRESH_INTERVAL")
        if not interval:
            return (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

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

        return limit.isoformat()

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} with {self.parameters} ...")

        try:
            self.execute()
        except Exception:
            logger.log_debug_trace(f"Refresh Bots Failed: {self.type}")
