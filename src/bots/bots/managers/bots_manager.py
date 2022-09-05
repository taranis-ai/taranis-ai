import threading
import importlib

from bots.managers.log_manager import logger
from bots.remote.core_api import CoreApi
from bots.config import Config


bots = {}


def register_bot_node():
    try:
        logger.log_debug(f"Registering bot Node at {Config.TARANIS_NG_CORE_URL}")
        response, code = CoreApi().register_node(get_registered_bots_info())
        if code == 200:
            logger.log_info(f"Successfully registered: {response}")
        return response, code
    except Exception:
        logger.log_critical("Registration failed")


def register_bot(bot):
    bots[bot.type] = bot


def initialize():
    logger.log_info(f"Initializing bot node: {Config.NODE_NAME}...")

    for c in Config.BOTS_LOADABLE_BOTS:
        module_ = importlib.import_module(f"bots.bots.{c.lower()}_bot")
        class_ = getattr(module_, f"{c}Bot")
        register_bot(class_())

    logger.log_info("Bot node initialized")


def refresh_bot(bot_type):
    if bot_type not in bots:
        return 403

    class RefreshThread(threading.Thread):
        @classmethod
        def run(cls):
            bots[bot_type].refresh()

    refresh_thread = RefreshThread()
    refresh_thread.start()
    return 200


def get_registered_bots_info():
    return [bots[key].get_info() for key in bots]


def process_event(event_type, data):
    for key in bots:
        bots[key].process_event(event_type, data)
