import json

from model.collector import Collector
from model.collectors_node import CollectorsNode
from model.osint_source import OSINTSource
from remote.collectors_api import CollectorsApi
from schema.collectors_node import CollectorsNode as CollectorNodeSchema
from schema.osint_source import OSINTSourceExportRootSchema, OSINTSourceExportRoot


def add_collectors_node(data):
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info("")

    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        node = CollectorsNode.add_new(data, collectors)

        collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)

    return status_code


def update_collectors_node(node_id, data):
    node = CollectorNodeSchema.create(data)
    collectors_info, status_code = CollectorsApi(node.api_url, node.api_key).get_collectors_info(node.id)
    if status_code == 200:
        collectors = Collector.create_all(collectors_info)
        CollectorsNode.update(node_id, data, collectors)

    return status_code


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


def refresh_collector(collector):
    return CollectorsApi(collector.node.api_url, collector.node.api_key).refresh_collector(collector.type)


def export_osint_sources(input_data):
    osint_sources = OSINTSource.get_all()
    if input_data is not None and 'selection' in input_data:
        data = []
        for osint_source in osint_sources[:]:
            if osint_source.id in input_data['selection']:
                data.append(osint_source)
    else:
        data = osint_sources

    schema = OSINTSourceExportRootSchema()
    export_data = schema.dump(OSINTSourceExportRoot(1, data))

    for osint_source in export_data['data']:
        for parameter_value in osint_source['parameter_values']:
            if parameter_value['parameter']['key'] == 'PROXY_SERVER':
                parameter_value['value'] = ''

    return json.dumps(export_data).encode('utf-8')


def import_osint_sources(collectors_node_id, file):
    collectors_node = CollectorsNode.get_by_id(collectors_node_id)

    file_data = file.read()
    json_data = json.loads(file_data.decode('utf8'))
    schema = OSINTSourceExportRootSchema()
    import_data = schema.load(json_data)

    collectors = set()
    for osint_source in import_data.data:
        collector = collectors_node.find_collector_by_type(osint_source.collector.type)
        if collector is not None:
            collectors.add(collector)
            OSINTSource.import_new(osint_source, collector)

    for collector in collectors:
        refresh_collector(collector)
