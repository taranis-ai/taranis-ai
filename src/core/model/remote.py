import uuid as uuid_generator
from datetime import datetime
from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_

from managers.db_manager import db
from model.osint_source import OSINTSource
from model.report_item_type import ReportItemType
from schema.osint_source import OSINTSourceIdSchema
from schema.remote import RemoteAccessSchema, RemoteAccessPresentationSchema, RemoteNodeSchema, RemoteNodePresentationSchema
from schema.report_item_type import ReportItemTypeIdSchema


class NewRemoteAccessSchema(RemoteAccessSchema):
    osint_sources = fields.Nested(OSINTSourceIdSchema, many=True)
    report_item_types = fields.Nested(ReportItemTypeIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return RemoteAccess(**data)


class RemoteAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    connected = db.Column(db.Boolean, default=False)
    access_key = db.Column(db.String(), unique=True)

    osint_sources = db.relationship('OSINTSource', secondary='remote_access_osint_source')
    report_item_types = db.relationship('ReportItemType', secondary='remote_access_report_item_type')

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime, default=datetime.now())
    last_synced_report_items = db.Column(db.DateTime, default=datetime.now())

    def __init__(self, id, name, description, enabled, access_key, osint_sources, report_item_types):
        self.id = None
        self.name = name
        self.description = description
        self.enabled = enabled
        self.access_key = access_key
        self.event_id = str(uuid_generator.uuid4())
        self.title = ""
        self.subtitle = ""
        self.tag = ""
        self.status = ''

        self.osint_sources = []
        for osint_source in osint_sources:
            self.osint_sources.append(OSINTSource.find(osint_source.id))

        self.report_item_types = []
        for report_item_type in report_item_types:
            self.report_item_types.append(ReportItemType.find(report_item_type.id))

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-remote-desktop"
        if self.enabled is False:
            self.status = 'red'
        elif self.connected is True:
            self.status = 'green'
        else:
            self.status = 'orange'

    @classmethod
    def exists_by_access_key(cls, access_key):
        return db.session.query(db.exists().where(RemoteAccess.access_key == access_key)).scalar()

    @classmethod
    def find_by_access_key(cls, access_key):
        remote_access = cls.query.filter(RemoteAccess.access_key == access_key).scalar()
        return remote_access

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(RemoteAccess.name).like(search_string),
                func.lower(RemoteAccess.description).like(search_string)))

        return query.order_by(db.asc(RemoteAccess.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        remote_accesses, count = cls.get(search)
        schema = RemoteAccessPresentationSchema(many=True)
        return {'total_count': count, 'items': schema.dump(remote_accesses)}

    @classmethod
    def get_relevant_for_news_items(cls, osint_source_ids):
        query = db.session.query(RemoteAccess.event_id).join(RemoteAccessOSINTSource, and_(
            RemoteAccessOSINTSource.remote_access_id == RemoteAccess.id,
            RemoteAccessOSINTSource.osint_source_id.in_(osint_source_ids)))

        response = query.all()
        ids = set()
        for rows in response:
            ids.add(rows[0])

        return list(ids)

    @classmethod
    def get_relevant_for_report_item(cls, report_type_id):
        query = db.session.query(RemoteAccess.event_id).join(RemoteAccessReportItemType, and_(
            RemoteAccessReportItemType.remote_access_id == RemoteAccess.id,
            RemoteAccessReportItemType.report_item_type_id == report_type_id))

        response = query.all()
        ids = set()
        for rows in response:
            ids.add(rows[0])

        return list(ids)

    @classmethod
    def add(cls, data):
        schema = NewRemoteAccessSchema()
        remote_access = schema.load(data)
        db.session.add(remote_access)
        db.session.commit()

    @classmethod
    def delete(cls, remote_access_id):
        remote_access = cls.query.get(remote_access_id)
        db.session.delete(remote_access)
        db.session.commit()

    @classmethod
    def update(cls, remote_access_id, data):
        schema = NewRemoteAccessSchema()
        updated_remote_access = schema.load(data)
        remote_access = cls.query.get(remote_access_id)
        remote_access.name = updated_remote_access.name
        remote_access.description = updated_remote_access.description
        remote_access.osint_sources = updated_remote_access.osint_sources
        remote_access.report_item_types = updated_remote_access.report_item_types

        disconnect = False
        event_id = remote_access.event_id

        if remote_access.enabled and not updated_remote_access.enabled:
            remote_access.enabled = False
            if remote_access.connected:
                remote_access.connected = False
                disconnect = True
        else:
            remote_access.enabled = updated_remote_access.enabled

        if remote_access.access_key != updated_remote_access.access_key or not remote_access.enabled:
            disconnect = True
            remote_access.connected = False
            remote_access.event_id = str(uuid_generator.uuid4())

        remote_access.access_key = updated_remote_access.access_key
        db.session.commit()

        return event_id, disconnect

    @classmethod
    def connect(cls, access_key):
        remote_access = cls.query.filter(RemoteAccess.access_key == access_key).scalar()
        if remote_access.enabled:
            remote_access.connected = True
            db.session.commit()
            return {'event_id': remote_access.event_id,
                    'last_synced_news_items': format(remote_access.last_synced_news_items),
                    'last_synced_report_items': format(remote_access.last_synced_report_items),
                    'news_items_provided': len(remote_access.osint_sources) > 0,
                    'report_items_provided': len(remote_access.report_item_types) > 0}
        else:
            return {'error': 'unauthorized'}, 401

    @classmethod
    def disconnect(cls, access_key):
        remote_access = cls.query.filter(RemoteAccess.access_key == access_key).scalar()
        remote_access.connected = False
        db.session.commit()

    def update_news_items_sync(self, data):
        self.last_synced_news_items = datetime.strptime(data['last_sync_time'], '%Y-%m-%d %H:%M:%S.%f')
        db.session.commit()

    def update_report_items_sync(self, data):
        self.last_synced_report_items = datetime.strptime(data['last_sync_time'], '%Y-%m-%d %H:%M:%S.%f')
        db.session.commit()


class RemoteAccessOSINTSource(db.Model):
    remote_access_id = db.Column(db.Integer, db.ForeignKey('remote_access.id'), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey('osint_source.id'), primary_key=True)


class RemoteAccessReportItemType(db.Model):
    remote_access_id = db.Column(db.Integer, db.ForeignKey('remote_access.id'), primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey('report_item_type.id'), primary_key=True)


class NewRemoteNodeSchema(RemoteNodeSchema):

    @post_load
    def make(self, data, **kwargs):
        return RemoteNode(**data)


class RemoteNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    remote_url = db.Column(db.String())
    events_url = db.Column(db.String())
    access_key = db.Column(db.String())

    sync_news_items = db.Column(db.Boolean)
    osint_source_group_id = db.Column(db.String, db.ForeignKey('osint_source_group.id'))
    sync_report_items = db.Column(db.Boolean)

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime)
    last_synced_report_items = db.Column(db.DateTime)

    def __init__(self, id, name, description, enabled, remote_url, events_url, access_key, sync_news_items,
                 sync_report_items, osint_source_group_id):
        self.id = None
        self.name = name
        self.description = description
        self.remote_url = remote_url
        self.events_url = events_url
        self.enabled = enabled
        self.access_key = access_key
        self.sync_news_items = sync_news_items
        self.sync_report_items = sync_report_items
        self.osint_source_group_id = osint_source_group_id
        self.title = ""
        self.subtitle = ""
        self.tag = ""
        self.status = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-share-variant"
        if self.enabled is False or not self.event_id:
            self.status = 'red'
        else:
            self.status = 'green'

    @classmethod
    def find(cls, node_id):
        return cls.query.get(node_id)

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(RemoteNode.name).like(search_string),
                func.lower(RemoteNode.description).like(search_string)))

        return query.order_by(db.asc(RemoteNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        remote_nodes, count = cls.get(search)
        schema = RemoteNodePresentationSchema(many=True)
        return {'total_count': count, 'items': schema.dump(remote_nodes)}

    @classmethod
    def add(cls, data):
        schema = NewRemoteNodeSchema()
        remote_node = schema.load(data)
        db.session.add(remote_node)
        db.session.commit()

    @classmethod
    def delete(cls, remote_node_id):
        remote_node = cls.query.get(remote_node_id)
        db.session.delete(remote_node)
        db.session.commit()

    @classmethod
    def update(cls, remote_node_id, data):
        schema = NewRemoteNodeSchema()
        updated_remote_node = schema.load(data)
        remote_node = cls.query.get(remote_node_id)
        remote_node.name = updated_remote_node.name
        remote_node.description = updated_remote_node.description
        remote_node.enabled = updated_remote_node.enabled
        remote_node.remote_url = updated_remote_node.remote_url
        remote_node.events_url = updated_remote_node.events_url
        remote_node.access_key = updated_remote_node.access_key
        remote_node.sync_news_items = updated_remote_node.sync_news_items
        remote_node.sync_report_items = updated_remote_node.sync_report_items
        remote_node.osint_source_group_id = updated_remote_node.osint_source_group_id
        if remote_node.enabled is False:
            remote_node.event_id = None
        db.session.commit()
        return remote_node.enabled

    def connect(self, access_info):
        self.event_id = access_info['event_id']
        self.last_synced_news_items = datetime.strptime(access_info['last_synced_news_items'], '%Y-%m-%d %H:%M:%S.%f')
        self.last_synced_report_items = datetime.strptime(access_info['last_synced_report_items'],
                                                          '%Y-%m-%d %H:%M:%S.%f')
        db.session.commit()

    def disconnect(self):
        self.event_id = None
        db.session.commit()
