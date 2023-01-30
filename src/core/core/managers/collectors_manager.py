import json
from requests.exceptions import ConnectionError

from core.model.collector import Collector
from core.model.collectors_node import CollectorsNode
from core.model.osint_source import OSINTSource
from core.remote.collectors_api import CollectorsApi
from core.managers.log_manager import logger
from shared.schema.collectors_node import CollectorsNode as CollectorNodeSchema
from shared.schema.osint_source import OSINTSourceExportRootSchema, OSINTSourceExportRoot


def get_collectors_info(node: CollectorNodeSchema):
    try:
        collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Collector Node: {node.name}")
        return f"Couldn't add Collector node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Collector.create_all(collectors_info), status_code


def add_collectors_node(data):
    try:
        logger.log_debug(f"ADD COLLECTOR: {data}")
        node = CollectorNodeSchema.create(data)

    except Exception as e:
        logger.log_debug_trace()
        return str(e), 500

    try:
        CollectorsNode.add_new(data)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Collector Node: {node.name}")
        return f"Couldn't add Collector node: {node.name}", 500

    return node.id, 200


def update_collectors_node(node_id, data):
    node = CollectorNodeSchema.create(data)
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
    osint_source = OSINTSource.add_new(data)
    refresh_collector(osint_source.collector)


def update_osint_source(osint_source_id, data):
    osint_source, default_group = OSINTSource.update(osint_source_id, data)
    refresh_collector(osint_source.collector)
    return osint_source, default_group


def delete_osint_source(osint_source_id):
    osint_source = OSINTSource.find(osint_source_id)
    collector = osint_source.collector
    OSINTSource.delete(osint_source_id)
    refresh_collector(collector)


def refresh_osint_source(osint_source_id):
    osint_source = OSINTSource.find(osint_source_id)
    refresh_collector(osint_source.collector)


def refresh_collector(collector):
    try:
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


def export_osint_sources(ids: list[str]):
    data = OSINTSource.get_all_by_id(ids) if ids else OSINTSource.get_all()

    schema = OSINTSourceExportRootSchema()
    export_data = schema.dump(OSINTSourceExportRoot(1, data))
    if "data" not in export_data:
        return None
    export_data = export_data["data"]
    export_data = cleanup_paramaters(export_data)
    return json.dumps(export_data).encode("utf-8")


def cleanup_paramaters(osint_sources: list) -> list:
    for osint_source in osint_sources:
        for parameter_value in osint_source["parameter_values"]:
            if parameter_value["parameter"]["key"] == "PROXY_SERVER":
                parameter_value["value"] = ""
    return osint_sources


def import_osint_sources(file):
    file_data = file.read()
    json_data = json.loads(file_data.decode("utf8"))
    import_data = OSINTSourceExportRootSchema().load(json_data).data

    for osint_source in import_data:
        OSINTSource.import_new(osint_source)
