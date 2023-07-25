from worker.log import logger
from worker.core_api import CoreApi


class BaseBot:
    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    def __init__(self):
        self.core_api = CoreApi()

    def execute(self):
        pass

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")

        try:
            self.execute()
        except Exception:
            logger.log_debug_trace(f"Refresh Bots Failed: {self.type}")
