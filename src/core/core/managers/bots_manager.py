from core.model.bots_node import BotsNode
from core.model.bot import Bot
from core.model.bot_preset import BotPreset
from core.remote.bots_api import BotsApi
from shared.schema.bots_node import BotsNode as BotsNodeSchema
from core.managers.log_manager import logger


def get_bots_info(node: BotsNodeSchema):
    try:
        bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Bot Node: {node.name}")
        return f"Couldn't add Bot node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Bot.create_all(bots_info), status_code


def add_bots_node(data):
    try:
        logger.log_info(data)
        bots_info = data.pop("bots_info")
        node = BotsNodeSchema.create(data)
    except Exception as e:
        logger.log_debug_trace()
        return str(e), 500

    try:
        bots = Bot.create_all(bots_info)
        BotsNode.add_new(data, bots)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Bot Node: {node.name}")
        return f"Couldn't add Bot Node: {node.name}", 500

    return node.id, 200


def update_bots_node(node_id, data):
    node = BotsNodeSchema.create(data)
    bots, status_code = get_bots_info(node)

    if status_code != 200:
        return bots, status_code

    try:
        BotsNode.update(node_id, data, bots)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Bot Node: {node.name}")
        return f"Couldn't add Bot node: {node.name}", 500

    return node.id, status_code


def verify_api_key(api_key):
    return BotsNode.exists_by_api_key(api_key)


def add_bot_preset(data):
    BotPreset.add_new(data)
