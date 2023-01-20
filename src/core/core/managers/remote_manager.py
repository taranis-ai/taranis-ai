import requests
import sseclient
import threading
import time
import json

from core.managers import sse_manager
from core.model.news_item import NewsItemAggregate
from core.model.remote import RemoteAccess, RemoteNode
from core.model.report_item import ReportItem
from core.remote.remote_api import RemoteApi

event_handlers = {}


class EventThread(threading.Thread):
    app = None

    def __init__(self, remote_node, event_handler):
        threading.Thread.__init__(self)
        self.remote_node = remote_node
        self.event_handler = event_handler

    def run(self):
        while not self.event_handler.is_set():
            try:
                response = requests.get(
                    self.remote_node.events_url + "?channel=remote&access_key=" + self.remote_node.access_key,
                    stream=True,
                )
                client = sseclient.SSEClient(response)
                for event in client.events():
                    data = json.loads(event.data)
                    if event.event == "remote_access_disconnect":
                        if self.remote_node.event_id in data:
                            with EventThread.app.app_context():
                                self.remote_node.disconnect()
                            return

                    elif event.event == "remote_access_news_items_updated":
                        if self.remote_node.sync_news_items and self.remote_node.osint_source_group_id is not None:
                            if self.remote_node.event_id in data:
                                data, status_code = RemoteApi(
                                    self.remote_node.remote_url,
                                    self.remote_node.access_key,
                                ).get_news_items()
                                if status_code == 200:
                                    with EventThread.app.app_context():
                                        NewsItemAggregate.add_remote_news_items(
                                            data["news_items"],
                                            self.remote_node,
                                            self.remote_node.osint_source_group_id,
                                        )

                                    RemoteApi(
                                        self.remote_node.remote_url,
                                        self.remote_node.access_key,
                                    ).confirm_news_items_sync({"last_sync_time": data["last_sync_time"]})

                                    with EventThread.app.app_context():
                                        sse_manager.news_items_updated()

                    elif event.event == "remote_access_report_items_updated":
                        if self.remote_node.sync_report_items:
                            if self.remote_node.event_id in data:
                                data, status_code = RemoteApi(
                                    self.remote_node.remote_url,
                                    self.remote_node.access_key,
                                ).get_report_items()
                                if status_code == 200:
                                    with EventThread.app.app_context():
                                        ReportItem.add_remote_report_items(data["report_items"], self.remote_node.name)

                                    RemoteApi(
                                        self.remote_node.remote_url,
                                        self.remote_node.access_key,
                                    ).confirm_report_items_sync({"last_sync_time": data["last_sync_time"]})

                                    with EventThread.app.app_context():
                                        sse_manager.report_items_updated()

            except Exception:
                time.sleep(5)


def connect_to_events(remote_node):
    event_handler = threading.Event()
    event_thread = EventThread(remote_node, event_handler)
    event_handlers[remote_node.id] = event_handler
    event_thread.start()


def disconnect_from_events(remote_node):
    if remote_node.id in event_handlers:
        event_handlers[remote_node.id].set()


def verify_access_key(access_key):
    return RemoteAccess.exists_by_access_key(access_key)


def connect_to_node(node_id):
    remote_node = RemoteNode.find(node_id)
    access_info, status_code = RemoteApi(remote_node.remote_url, remote_node.access_key).connect()
    if status_code == 200:
        remote_node.connect(access_info)
        connect_to_events(remote_node)
    else:
        remote_node.disconnect()
        disconnect_from_events(remote_node)

    return access_info, status_code


def disconnect_from_node(node_id):
    remote_node = RemoteNode.find(node_id)
    RemoteApi(remote_node.remote_url, remote_node.access_key).disconnect()


def initialize(app):
    EventThread.app = app
    remote_nodes, _ = RemoteNode.get()
    for remote_node in remote_nodes:
        if remote_node.enabled:
            connect_to_node(remote_node.id)
