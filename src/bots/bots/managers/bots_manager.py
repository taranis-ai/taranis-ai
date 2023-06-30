import importlib

from bots.managers.log_manager import logger
from bots.remote.core_api import CoreApi
from bots.config import settings
from shared.schema.bot import BotImportSchema


bots = {}


def register_bot(bot):
    bots[bot.type] = bot

def initialize():
    CoreApi().register_node()
    logger.log_info(f"Initializing bot node: {settings.NODE_NAME}...")
    try:
        bots = CoreApi().get_bots()
        if not bots:
            logger.warning(f"No Bots in BotInfo: {bots}")
            return

    except Exception:
        logger.warning(f"Couldn't parse Bot info: {bots}")
        return

    paramaters = {bot['type']: bot[bot['type']] for bot in bots}

    for c in settings.BOTS_LOADABLE_BOTS:
        module_ = importlib.import_module(f"bots.bots.{c.lower()}_bot")
        class_ = getattr(module_, f"{c}Bot")
        register_bot(class_(paramaters[f"{c.upper()}_BOT"]))

    logger.log_info("Bot node initialized")


def refresh():
    return next((500 for bot_type in bots if refresh_bot(bot_type) != 200), 200)


def refresh_bot(bot_type):
    if bot_type not in bots:
        return 403

    bots[bot_type].refresh()
    return 200


def get_registered_bots_info():
    return [bots[key].get_info() for key in bots]


def process_event(event_type, data):
    for key in bots:
        bots[key].execute_on_event(event_type, data)
