from model.publishers_node import PublishersNode
from model.publisher import Publisher
from model.publisher_preset import PublisherPreset
from remote.publishers_api import PublishersApi
from schema.publishers_node import PublishersNode as PublishersNodeSchema
from schema.publisher import PublisherInput, PublisherInputSchema


def add_publishers_node(data):
    node = PublishersNodeSchema.create(data)
    publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    if status_code == 200:
        publishers = Publisher.create_all(publishers_info)
        PublishersNode.add_new(data, publishers)

    return status_code


def update_publishers_node(node_id, data):
    node = PublishersNodeSchema.create(data)
    publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    if status_code == 200:
        publishers = Publisher.create_all(publishers_info)
        PublishersNode.update(node_id, data, publishers)

    return status_code


def add_publisher_preset(data):
    PublisherPreset.add_new(data)


def publish(preset, data, message_title, message_body, recipients):
    publisher = preset.publisher
    node = publisher.node
    data_data = None
    data_mime = None
    if data is not None:
        data_data = data['data']
        data_mime = data['mime_type']

    input_data = PublisherInput(publisher.type, preset.parameter_values, data_mime, data_data, message_title,
                                message_body, recipients)
    input_schema = PublisherInputSchema()

    return PublishersApi(node.api_url, node.api_key).publish(input_schema.dump(input_data))
