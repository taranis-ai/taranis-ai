from core.model.bots_node import BotsNode
from core.model.bot import Bot
from core.remote.bots_api import BotsApi
from core.managers.log_manager import logger


def get_bots_info(node: BotsNode):
    try:
        bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Bot Node: {node.name}")
        return f"Couldn't add Bot node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Bot.load_multiple(bots_info), status_code


def refresh_bots():
    try:
        if node := BotsNode.get_first():
            BotsApi(node.api_url, node.api_key).refresh_bots()
    except ConnectionError:
        logger.critical("Connection error: Could not reach Bot")


def update_bots_node(node_id, data):
    node = BotsNode.get(node_id)
    bots, status_code = get_bots_info(node)

    if status_code != 200:
        return bots, status_code

    try:
        BotsNode.update(node_id, data)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Bot Node: {node.name}")
        return f"Couldn't add Bot node: {node.name}", 500

    return node.id, status_code


def verify_api_key(api_key):
    return BotsNode.exists_by_api_key(api_key)
