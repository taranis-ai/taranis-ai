from core.model.bots_node import BotsNode
from core.model.bot import Bot
from core.model.bot_preset import BotPreset
from core.remote.bots_api import BotsApi
from shared.schema.bots_node import BotsNode as BotsNodeSchema
from core.managers.log_manager import logger


def add_bots_node(data):
    node = BotsNodeSchema.create(data)
    try:
        bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
        logger.info(bots_info)
        if status_code == 200:
            bots = Bot.create_all(bots_info)
            BotsNode.add_new(data, bots)
            return "Successfully added {bots_info.bot_type}", status_code

        return "", status_code
    except Exception:
        return "Error Adding Bot", 500


def update_bots_node(node_id, data):
    node = BotsNodeSchema.create(data)
    bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
    if status_code == 200:
        bots = Bot.create_all(bots_info)
        BotsNode.update(node_id, data, bots)

    return status_code


def verify_api_key(api_key):
    return BotsNode.exists_by_api_key(api_key)


def add_bot_preset(data):
    BotPreset.add_new(data)
