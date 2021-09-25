from model.collectors_node import CollectorsNode
from model.collector import Collector
from model.osint_source import OSINTSource
from remote.collectors_api import CollectorsApi
from taranisng.schema import collectors_node


def add_collectors_node(data):
    node = collectors_node.CollectorsNode.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info()
    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        CollectorsNode.add_new(data, collectors)

    return status_code


def update_collectors_node(node_id, data):
    node = collectors_node.CollectorsNode.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info()
    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        CollectorsNode.update(node_id, data, collectors)

    return status_code


def add_osint_source(data):
    OSINTSource.add_new(data)
