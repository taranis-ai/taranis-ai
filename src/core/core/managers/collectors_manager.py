import json
from requests.exceptions import ConnectionError

from core.model.collector import Collector
from core.model.collectors_node import CollectorsNode
from core.model.osint_source import OSINTSource
from core.remote.collectors_api import CollectorsApi
from core.managers.log_manager import logger


def get_collectors_info(node: CollectorsNode):
    try:
        collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Collector Node: {node.name}")
        return f"Couldn't add Collector node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Collector.load_multiple(collectors_info), status_code


def update_collectors_node(node_id, data):
    node = CollectorsNode.get(node_id)
    collectors, status_code = get_collectors_info(node)
    if status_code != 200:
        return collectors, status_code

    try:
        CollectorsNode.update(node_id, data)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Collector Node: {node.name}")
        return f"Couldn't add Collector node: {node.name}", 500

    return node.id, status_code


def add_osint_source(data):
    osint_source = OSINTSource.add(data)
    refresh_collector(osint_source.collector_id)
    return {"id": osint_source.id, "message": "OSINT source created successfully"}, 201


def update_osint_source(osint_source_id, data):
    osint_source, default_group = OSINTSource.update(osint_source_id, data)
    refresh_collector(osint_source.collector_id)
    return osint_source, default_group


def delete_osint_source(osint_source_id):
    osint_source = OSINTSource.get(osint_source_id)
    if not osint_source:
        return f"OSINT Source with ID: {osint_source_id} not found", 404
    OSINTSource.delete(osint_source.id)
    refresh_collector(osint_source.collector_id)
    return f"OSINT Source {osint_source.name} deleted", 200


def refresh_osint_source(osint_source_id):
    osint_source = OSINTSource.get(osint_source_id)
    refresh_collector(osint_source.collector_id)


def refresh_collector(collector_id):
    try:
        collector = Collector.get(collector_id)
        if node := CollectorsNode.get_first():
            CollectorsApi(node.api_url, node.api_key).refresh_collector(collector.type)
    except ConnectionError:
        logger.critical("Connection error: Could not reach Collector")


def refresh_collectors():
    try:
        if node := CollectorsNode.get_first():
            CollectorsApi(node.api_url, node.api_key).refresh_collectors()
    except ConnectionError:
        logger.critical("Connection error: Could not reach Collector")


def export_osint_sources():
    data = OSINTSource.get_all()
    data = cleanup_paramaters(data)
    export_data = {"version": 2, "data": [osint_source.to_export_dict() for osint_source in data]}
    return json.dumps(export_data).encode("utf-8")


def cleanup_paramaters(osint_sources: list) -> list:
    for osint_source in osint_sources:
        for parameter_value in osint_source.parameter_values:
            if parameter_value.parameter.key == "PROXY_SERVER":
                parameter_value.value = ""
    return osint_sources


def parse_version_1(data: list) -> list:
    for source in data:
        for parameter in source["parameter_values"]:
            parameter["parameter"] = parameter["parameter"]["key"]
    return data


def import_osint_sources(file):
    file_data = file.read()
    json_data = json.loads(file_data.decode("utf8"))
    data = parse_version_1(json_data["data"]) if json_data["version"] == 1 else json_data["data"]
    return OSINTSource.add_multiple(data)
