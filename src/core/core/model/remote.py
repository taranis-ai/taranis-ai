import uuid as uuid_generator
from datetime import datetime
from sqlalchemy import orm, func, or_, and_
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.osint_source import OSINTSource
from core.model.report_item_type import ReportItemType


class RemoteAccess(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    connected = db.Column(db.Boolean, default=False)
    access_key = db.Column(db.String(), unique=True)

    osint_sources = db.relationship("OSINTSource", secondary="remote_access_osint_source")
    report_item_types = db.relationship("ReportItemType", secondary="remote_access_report_item_type")

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime, default=datetime.now())
    last_synced_report_items = db.Column(db.DateTime, default=datetime.now())

    def __init__(
        self,
        id,
        name,
        description,
        enabled,
        access_key,
        osint_sources,
        report_item_types,
    ):
        self.id = None
        self.name = name
        self.description = description
        self.enabled = enabled
        self.access_key = access_key
        self.event_id = str(uuid_generator.uuid4())
        self.status = ""

        self.osint_sources = []
        self.osint_sources.extend(OSINTSource.get(osint_source.id) for osint_source in osint_sources)
        self.report_item_types = []
        self.report_item_types.extend(ReportItemType.get(report_item_type.id) for report_item_type in report_item_types)

    @orm.reconstructor
    def reconstruct(self):
        if not self.enabled:
            self.status = "red"
        elif self.connected:
            self.status = "green"
        else:
            self.status = "orange"

    @classmethod
    def exists_by_access_key(cls, access_key):
        return db.session.query(db.exists().where(RemoteAccess.access_key == access_key)).scalar()

    @classmethod
    def find_by_access_key(cls, access_key):
        return cls.query.filter(RemoteAccess.access_key == access_key).scalar()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    func(RemoteAccess.name).ilike(f"%{search}%"),
                    func(RemoteAccess.description).ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(RemoteAccess.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        remote_accesses, count = cls.get(search)
        items = [remote_access.to_dict() for remote_access in remote_accesses]
        return {"total_count": count, "items": items}

    @classmethod
    def get_relevant_for_news_items(cls, osint_source_ids) -> set[int]:
        query = db.session.query(RemoteAccess.event_id).join(
            RemoteAccessOSINTSource,
            and_(
                RemoteAccessOSINTSource.remote_access_id == RemoteAccess.id,
                RemoteAccessOSINTSource.osint_source_id.in_(osint_source_ids),
            ),
        )

        response = query.all()
        return {rows.id for rows in response}

    @classmethod
    def get_relevant_for_report_item(cls, report_type_id) -> set[int]:
        query = db.session.query(RemoteAccess.event_id).join(
            RemoteAccessReportItemType,
            and_(
                RemoteAccessReportItemType.remote_access_id == RemoteAccess.id,
                RemoteAccessReportItemType.report_item_type_id == report_type_id,
            ),
        )

        response = query.all()
        return {rows.id for rows in response}

    @classmethod
    def update(cls, remote_access_id, data) -> tuple[str, int]:
        remote_access = cls.query.get(remote_access_id)
        if not remote_access:
            return "Remote access not found", 404
        for key, value in data.items():
            if hasattr(remote_access, key) and key != "id":
                setattr(remote_access, key, value)
        db.session.commit()
        return "Remote access updated", 200

    @classmethod
    def connect(cls, access_key):
        remote_access = cls.query.filter(RemoteAccess.access_key == access_key).scalar()
        if remote_access.enabled:
            remote_access.connected = True
            db.session.commit()
            return {
                "event_id": remote_access.event_id,
                "last_synced_news_items": format(remote_access.last_synced_news_items),
                "last_synced_report_items": format(remote_access.last_synced_report_items),
                "news_items_provided": len(remote_access.osint_sources) > 0,
                "report_items_provided": len(remote_access.report_item_types) > 0,
            }
        else:
            return {"error": "unauthorized"}, 401

    @classmethod
    def disconnect(cls, access_key):
        remote_access = cls.query.filter(RemoteAccess.access_key == access_key).scalar()
        remote_access.connected = False
        db.session.commit()

    def update_news_items_sync(self, data):
        self.last_synced_news_items = datetime.strptime(data["last_sync_time"], "%Y-%m-%d %H:%M:%S.%f")
        db.session.commit()

    def update_report_items_sync(self, data):
        self.last_synced_report_items = datetime.strptime(data["last_sync_time"], "%Y-%m-%d %H:%M:%S.%f")
        db.session.commit()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemoteAccess":
        return cls(**data)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["osint_sources"] = [osint_source.id for osint_source in self.osint_sources]
        data["report_item_types"] = [report_item_type.id for report_item_type in self.report_item_types]
        data["tag"] = "mdi-remote-desktop"
        if not self.enabled:
            data["status"] = "red"
        elif self.connected:
            data["status"] = "green"
        else:
            data["status"] = "orange"

        return data

    @classmethod
    def load_multiple(cls, json_data: list[dict[str, Any]]) -> list["RemoteAccess"]:
        return [cls.from_dict(data) for data in json_data]


class RemoteAccessOSINTSource(BaseModel):
    remote_access_id = db.Column(db.Integer, db.ForeignKey("remote_access.id"), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), primary_key=True)


class RemoteAccessReportItemType(BaseModel):
    remote_access_id = db.Column(db.Integer, db.ForeignKey("remote_access.id"), primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), primary_key=True)


class RemoteNode(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    enabled = db.Column(db.Boolean)
    remote_url = db.Column(db.String())
    events_url = db.Column(db.String())
    access_key = db.Column(db.String())

    sync_news_items = db.Column(db.Boolean)
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id"))
    sync_report_items = db.Column(db.Boolean)

    event_id = db.Column(db.String(64), unique=True)
    last_synced_news_items = db.Column(db.DateTime)
    last_synced_report_items = db.Column(db.DateTime)

    def __init__(
        self,
        name,
        description,
        enabled,
        remote_url,
        events_url,
        access_key,
        sync_news_items,
        sync_report_items,
        osint_source_group_id,
        id=None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.remote_url = remote_url
        self.events_url = events_url
        self.enabled = enabled
        self.access_key = access_key
        self.sync_news_items = sync_news_items
        self.sync_report_items = sync_report_items
        self.osint_source_group_id = osint_source_group_id

    @classmethod
    def get_by_filter(cls, search=None):
        query = cls.query

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    RemoteNode.name.ilike(search_string),
                    RemoteNode.description.ilike(search_string),
                )
            )

        return query.order_by(db.asc(RemoteNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        remote_nodes, count = cls.get_by_filter(search)
        items = [remote_node.to_dict() for remote_node in remote_nodes]
        return {"total_count": count, "items": items}

    @classmethod
    def update(cls, remote_node_id, data) -> tuple[str, int]:
        remote_node = cls.query.get(remote_node_id)
        if not remote_node:
            return "Remote node not found", 404
        for key, value in data.items():
            if hasattr(remote_node, key) and key != "id":
                setattr(remote_node, key, value)
        db.session.commit()
        return f"Remote node {remote_node.name} updated", 200

    def connect(self, access_info):
        self.event_id = access_info["event_id"]
        self.last_synced_news_items = datetime.fromisoformat(access_info["last_synced_news_items"])
        self.last_synced_report_items = datetime.fromisoformat(access_info["last_synced_report_items"])
        db.session.commit()

    def disconnect(self):
        self.event_id = None
        db.session.commit()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RemoteAccess":
        return cls(**data)

    def to_dict(self):
        data = super().to_dict()

        data["tag"] = "mdi-share-variant"
        data["status"] = "red" if not self.enabled or not self.event_id else "green"
        return data

    @classmethod
    def load_multiple(cls, json_data: list[dict[str, Any]]) -> list["RemoteAccess"]:
        return [cls.from_dict(data) for data in json_data]
