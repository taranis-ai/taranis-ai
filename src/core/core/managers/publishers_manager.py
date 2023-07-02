from core.model.publishers_node import PublishersNode
from core.model.publisher import Publisher
from core.remote.publishers_api import PublishersApi
from core.managers.log_manager import logger


def get_publishers_info(node: PublishersNode) -> tuple[list[Publisher] | str, int]:
    try:
        publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Publisher Node: {node.name}")
        return f"Couldn't add Publisher node: {node.name}", 500

    if status_code != 200:
        return publishers_info, status_code

    return Publisher.load_multiple(publishers_info), status_code


def add_publishers_node(data):
    try:
        logger.log_info(data)
        publishers_info = data.pop("publishers_info")
    except Exception as e:
        logger.log_debug_trace()
        return str(e), 500

    try:
        publishers = Publisher.load_multiple(publishers_info)
        node = PublishersNode.add(data, publishers)
    except Exception:
        logger.log_debug_trace("Couldn't add Publisher Node")
        return "Couldn't add Publisher Node", 500

    return {"id": node.id, "message": "Added node"}, 200


def update_publishers_node(node_id, data):
    node = PublishersNode.get(node_id)
    if not node:
        return
    publishers, status_code = get_publishers_info(node)

    if status_code != 200:
        return publishers, status_code

    try:
        PublishersNode.update(node_id, data, publishers)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Publisher Node: {node.name}")
        return f"Couldn't add Publisher node: {node.name}", 500

    return node.id, status_code


def publish(preset, data, message_title, message_body, recipients):
    publisher = preset.publisher
    node = publisher.node
    data_data = None
    data_mime = None
    if data is not None:
        data_data = data["data"]
        data_mime = data["mime_type"]

    input_data = {
        "type": publisher.type,
        "parameter_values": preset.parameter_values,
        "mime_type": data_mime,
        "data": data_data,
        "message_title": message_title,
        "message_body": message_body,
        "recipients": recipients,
    }

    return PublishersApi(node.api_url, node.api_key).publish(input_data)
