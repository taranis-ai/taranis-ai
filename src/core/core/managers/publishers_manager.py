from core.remote.publishers_api import PublishersApi
from core.managers.log_manager import logger


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
