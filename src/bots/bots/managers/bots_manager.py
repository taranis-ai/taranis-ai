import importlib

from bots.managers.log_manager import logger
from bots.remote.core_api import CoreApi
from bots.config import Config
from shared.schema.bot import BotSchema


bots = {}


def register_bot(bot):
    bots[bot.type] = bot


def initialize():
    CoreApi().register_node()

    logger.log_info(f"Initializing bot node: {Config.NODE_NAME}...")

    response = CoreApi().get_bots()

    if not response:
        logger.log_debug(f"Couldn't get Bot info: {response}")
        return

    bot_schema = BotSchema(many=True)
    bots = bot_schema.load(response)
    parameters = {}
    for bot in bots:
        parameters[bot['type']] = {}
        for item in bot['parameter_values']:
            parameters[bot['type']][item.parameter.key] = item.value

    for c in Config.BOTS_LOADABLE_BOTS:
        module_ = importlib.import_module(f"bots.bots.{c.lower()}_bot")
        class_ = getattr(module_, f"{c}Bot")
        register_bot(class_(parameters[f"{c.upper()}_BOT"]))

    logger.log_info("Bot node initialized")


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
