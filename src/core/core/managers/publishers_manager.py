from core.model.publishers_node import PublishersNode
from core.model.publisher import Publisher
from core.remote.publishers_api import PublishersApi
from core.model.publisher_preset import PublisherPreset
from core.managers.log_manager import logger

from shared.schema.publishers_node import PublishersNode as PublishersNodeSchema
from shared.schema.publisher import PublisherInput, PublisherInputSchema


def get_publishers_info(node: PublishersNodeSchema):
    try:
        publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Publisher Node: {node.name}")
        return f"Couldn't add Publisher node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Publisher.create_all(publishers_info), status_code


def add_publishers_node(data):
    try:
        logger.log_info(data)
        publishers_info = data.pop("publishers_info")
        node = PublishersNodeSchema.create(data)
    except Exception as e:
        logger.log_debug_trace()
        return str(e), 500

    try:
        publishers = Publisher.create_all(publishers_info)
        PublishersNode.add_new(data, publishers)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Publisher Node: {node.name}")
        return f"Couldn't add Publisher Node: {node.name}", 500

    return node.id, 200


def update_publishers_node(node_id, data):
    node = PublishersNodeSchema.create(data)
    publishers, status_code = get_publishers_info(node)

    if status_code != 200:
        return publishers, status_code

    try:
        PublishersNode.update(node_id, data, publishers)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Publisher Node: {node.name}")
        return f"Couldn't add Publisher node: {node.name}", 500

    return node.id, status_code


def add_publisher_preset(data):
    PublisherPreset.add_new(data)


def publish(preset, data, message_title, message_body, recipients):
    publisher = preset.publisher
    node = publisher.node
    data_data = None
    data_mime = None
    if data is not None:
        data_data = data["data"]
        data_mime = data["mime_type"]

    input_data = PublisherInput(
        publisher.type,
        preset.parameter_values,
        data_mime,
        data_data,
        message_title,
        message_body,
        recipients,
    )
    input_schema = PublisherInputSchema()

    return PublishersApi(node.api_url, node.api_key).publish(input_schema.dump(input_data))
