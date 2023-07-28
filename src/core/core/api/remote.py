from flask import request
from flask_restx import Resource, Namespace, Api

from core.managers import auth_manager
from core.managers.auth_manager import access_key_required
from core.model import news_item, remote, report_item


class RemoteConnect(Resource):
    @access_key_required
    def get(self):
        return remote.RemoteAccess.connect(auth_manager.get_access_key())


class RemoteDisconnect(Resource):
    @access_key_required
    def get(self):
        return remote.RemoteAccess.disconnect(auth_manager.get_access_key())


class RemoteSyncNewsItems(Resource):
    @access_key_required
    def get(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        news_items, last_sync_time = news_item.NewsItemData.get_for_sync(remote_access.last_synced_news_items, remote_access.osint_sources)
        return {"last_sync_time": format(last_sync_time), "news_items": news_items}

    @access_key_required
    def put(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        remote_access.update_news_items_sync(request.json)


class RemoteSyncReportItems(Resource):
    @access_key_required
    def get(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        report_items, last_sync_time = report_item.ReportItem.get_for_sync(
            remote_access.last_synced_report_items, remote_access.report_item_types
        )
        return {"last_sync_time": format(last_sync_time), "report_items": report_items}

    @access_key_required
    def put(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        remote_access.update_report_items_sync(request.json)


def initialize(api: Api):
    namespace = Namespace("remote", description="Remote access API", path="")
    namespace.add_resource(RemoteConnect, "/connect")
    namespace.add_resource(RemoteDisconnect, "/disconnect")
    namespace.add_resource(RemoteSyncNewsItems, "/sync-news-items")
    namespace.add_resource(RemoteSyncReportItems, "/sync-report-items")
    api.add_namespace(namespace)
