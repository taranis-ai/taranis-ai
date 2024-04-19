import uuid
import json
import base64
from datetime import datetime
from typing import Any
from sqlalchemy import or_
from sqlalchemy.orm import deferred, Mapped
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.log import logger
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.parameter_value import ParameterValue
from core.model.word_list import WordList
from core.model.base_model import BaseModel
from core.model.queue import ScheduleEntry
from core.model.worker import COLLECTOR_TYPES, Worker
from core.service.role_based_access import RoleBasedAccessService, RBACQuery


class OSINTSource(BaseModel):
    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    type: Any = db.Column(db.Enum(COLLECTOR_TYPES))
    parameters: Any = db.relationship(
        "ParameterValue",
        secondary="osint_source_parameter_value",
        cascade="all, delete",
    )  # type: ignore
    groups: Any = db.relationship("OSINTSourceGroup", secondary="osint_source_group_osint_source")  # type: ignore

    icon: Any = deferred(db.Column(db.LargeBinary))
    state = db.Column(db.SmallInteger, default=0)
    last_collected = db.Column(db.DateTime, default=None)
    last_attempted = db.Column(db.DateTime, default=None)
    last_error_message = db.Column(db.String, default=None)

    def __init__(self, name, description, type, parameters=None, icon=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        if icon is not None and (icon_data := self.is_valid_base64(icon)):
            self.icon = icon_data

        self.parameters = Worker.parse_parameters(type, parameters)

    @classmethod
    def get_all(cls) -> list["OSINTSource"]:
        return (
            db.session.execute(
                db.select(cls)
                .where(cls.type != COLLECTOR_TYPES.MANUAL_COLLECTOR)
                .order_by(
                    db.nulls_first(db.asc(cls.last_collected)),
                    db.nulls_first(db.asc(cls.last_attempted)),
                )
            )
            .scalars()
            .all()
        )

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(or_(cls.name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%"), cls.type.ilike(f"%{search}%")))

        if source_type := filter_args.get("type"):
            query = query.where(cls.type == source_type)

        return query.order_by(db.asc(cls.name))

    def update_icon(self, icon):
        self.icon = icon
        db.session.commit()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OSINTSource":
        drop_keys = ["last_collected", "last_attempted", "state", "last_error_message"]
        [data.pop(key, None) for key in drop_keys if key in data]
        return cls(**data)

    def to_dict(self):
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters if parameter.value}
        data["icon"] = base64.b64encode(self.icon).decode("utf-8") if self.icon else None
        return data

    def to_worker_dict(self):
        data = super().to_dict()
        data.pop("icon", None)
        data["word_lists"] = []
        for group in self.groups:
            data["word_lists"].extend([word_list.to_dict() for word_list in group.word_lists])
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters if parameter.value}
        return data

    def to_task_id(self):
        return f"osint_source_{self.id}_{self.type}"

    def get_schedule(self):
        refresh_interval = ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL")
        return refresh_interval or "480"

    def to_task_dict(self):
        return {
            "id": self.to_task_id(),
            "task": "collector_task",
            "schedule": self.get_schedule(),
            "args": [self.id],
            "options": {"queue": "collectors"},
        }

    @classmethod
    def add(cls, data):
        osint_source = cls.from_dict(data)
        db.session.add(osint_source)
        OSINTSourceGroup.add_source_to_default(osint_source)
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    def is_valid_base64(self, s) -> bytes | None:
        try:
            return base64.b64decode(s, validate=True)
        except Exception:
            return None

    @classmethod
    def update(cls, osint_source_id, data):
        osint_source = cls.get(osint_source_id)
        if not osint_source:
            return None
        if name := data.get("name"):
            osint_source.name = name
        osint_source.description = data.get("description")
        icon_str = data.get("icon")
        if icon_str is not None and (icon := osint_source.is_valid_base64(icon_str)):
            osint_source.icon = icon
        if parameters := data.get("parameters"):
            update_parameter = ParameterValue.get_or_create_from_list(parameters)
            osint_source.parameters = ParameterValue.get_update_values(osint_source.parameters, update_parameter)
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    @classmethod
    def delete(cls, id) -> tuple[str, int]:
        if source := cls.get(id):
            try:
                source.unschedule_osint_source()
                db.session.delete(source)
                db.session.commit()
                return f"{cls.__name__} {id} deleted", 200
            except IntegrityError as e:
                logger.warning(f"IntegrityError: {e.orig}")

        return f"{cls.__name__} {id} not found", 404

    def update_status(self, error_message=None):
        self.last_attempted = datetime.now()
        if error_message:
            logger.error(f"Updating status for {self.id} with error message {error_message}")
            self.state = 1
        else:
            self.last_collected = datetime.now()
            self.state = 0
            if schedule_entry := ScheduleEntry.get(self.to_task_id()):
                schedule_entry.last_run_at = datetime.now()
        self.last_error_message = error_message
        db.session.commit()

    def schedule_osint_source(self):
        if self.type == COLLECTOR_TYPES.MANUAL_COLLECTOR:
            return {"message": "Manual collector does not need to be scheduled"}, 200
        entry = self.to_task_dict()
        ScheduleEntry.add_or_update(entry)
        logger.info(f"Schedule for source {self.id} updated with - {entry}")
        return {"message": f"Schedule for source {self.id} updated"}, 200

    def unschedule_osint_source(self):
        entry_id = self.to_task_dict()["id"]
        ScheduleEntry.delete(entry_id)
        logger.info(f"Schedule for source {self.id} removed")
        return {"message": f"Schedule for source {self.id} removed"}, 200

    def to_export_dict(self, id_to_index_map: dict):
        export_dict = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "parameters": [parameter.to_dict() for parameter in self.parameters if parameter.value],
        }
        # test if source is in a group that is not default
        if any(group for group in self.groups if not group.default):
            export_dict["group_idx"] = id_to_index_map.get(self.id)
        return export_dict

    @classmethod
    def export_osint_sources(cls, source_ids=None) -> bytes:
        query = db.select(cls)
        if source_ids:
            query = query.filter(cls.id.in_(source_ids))

        data = cls.get_filtered(query)
        if not data:
            return json.dumps({"error": "no sources found"}).encode("utf-8")

        id_to_index_map = {}
        for idx, osint_source in enumerate(data, 1):
            osint_source.cleanup_parameters()
            id_to_index_map[osint_source.id] = idx

        groups = OSINTSourceGroup.get_all_without_default() or []
        export_data = {
            "version": 3,
            "sources": [osint_source.to_export_dict(id_to_index_map) for osint_source in data],
            "groups": [group.to_export_dict(id_to_index_map) for group in groups],
        }
        logger.debug(f"Exporting {len(export_data['sources'])} sources")
        return json.dumps(export_data).encode("utf-8")

    def cleanup_parameters(self) -> "OSINTSource":
        for parameter in self.parameters:
            if parameter.parameter == "PROXY_SERVER":
                parameter.value = ""
        return self

    @classmethod
    def parse_version_1(cls, data: list) -> list:
        for source in data:
            source["parameters"] = []
            for parameter in source.pop("parameter_values", []):
                source["parameters"].append(
                    {
                        parameter["parameter"]["key"]: parameter["value"],
                    }
                )
            source["type"] = source.pop("collector")["type"]
        return data

    @classmethod
    def add_multiple_with_group(cls, sources, groups) -> list:
        index_to_id_mapping = {}
        for data in sources:
            idx = data.pop("group_idx", None)
            item = cls.from_dict(data)
            db.session.add(item)
            item.schedule_osint_source()
            OSINTSourceGroup.add_source_to_default(item)

            index_to_id_mapping[idx or item.id] = item.id

        for group in groups:
            group["osint_sources"] = [index_to_id_mapping.get(idx) for idx in group["osint_sources"] if idx]
            OSINTSourceGroup.add(group)

        db.session.commit()
        return list(index_to_id_mapping.values())

    @classmethod
    def import_osint_sources(cls, file):
        file_data = file.read()
        json_data = json.loads(file_data.decode("utf8"))
        groups = []
        if json_data["version"] == 1:
            data = cls.parse_version_1(json_data["data"])
        elif json_data["version"] == 2:
            data = json_data["data"]
        elif json_data["version"] == 3:
            data = json_data["sources"]
            groups = json_data["groups"]
        else:
            raise ValueError("Unsupported version")

        ids = cls.add_multiple_with_group(data, groups)
        logger.debug(f"Imported {len(ids)} sources")
        return ids


class OSINTSourceParameterValue(BaseModel):
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id", ondelete="CASCADE"), primary_key=True)


class OSINTSourceGroup(BaseModel):
    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    default: Mapped[bool] = db.Column(db.Boolean(), default=False)

    osint_sources: Any = db.relationship(
        "OSINTSource",
        secondary="osint_source_group_osint_source",
        back_populates="groups",
    )
    word_lists: Any = db.relationship("WordList", secondary="osint_source_group_word_list")  # type: ignore

    def __init__(self, name, description="", osint_sources=None, default=False, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.default = default
        self.osint_sources = [OSINTSource.get(osint_source) for osint_source in osint_sources] if osint_sources else []
        self.word_lists = [WordList.get(word_list) for word_list in word_lists] if word_lists else []

    @classmethod
    def get_all_without_default(cls):
        return cls.get_filtered(db.select(cls).filter(OSINTSourceGroup.default.is_(False)).order_by(db.asc(OSINTSourceGroup.name)))

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE_GROUP)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(or_(cls.name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%")))

        return query.order_by(db.asc(cls.name))

    def to_word_list_dict(self):
        flat_entry_list = []
        word_list_entries = [word_list.to_entry_dict() for word_list in self.word_lists if word_list]
        for sublist in word_list_entries:
            flat_entry_list.extend(sublist)
        return flat_entry_list, 200

    @classmethod
    def get_default(cls):
        return cls.get_first(db.select(cls).filter(OSINTSourceGroup.default))

    @classmethod
    def add_source_to_default(cls, osint_source: OSINTSource):
        default_group = cls.get_default()
        if not default_group:
            default_group = cls(name="Default", default=True)
            db.session.add(default_group)
            db.session.commit()
        default_group.osint_sources.append(osint_source)
        db.session.commit()

    def to_export_dict(self, source_mapping: dict) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "osint_sources": [
                source_mapping[osint_source.id] for osint_source in self.osint_sources if osint_source and osint_source.id in source_mapping
            ],
        }

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(
            user=user, resource_id=self.id, resource_type=ItemType.OSINT_SOURCE_GROUP, require_write_access=require_write_access
        )

        return RoleBasedAccessService.user_has_access_to_resource(query)

    def to_dict(self):
        data = super().to_dict()
        data["osint_sources"] = [osint_source.id for osint_source in self.osint_sources if osint_source]
        data["word_lists"] = [word_list.id for word_list in self.word_lists if word_list]
        return data

    @classmethod
    def delete(cls, osint_source_group_id):
        osint_source_group = cls.get(osint_source_group_id)
        if not osint_source_group:
            return {"message": "No Sourcegroup found"}, 404
        if osint_source_group.default is True:
            return {"message": "could_not_delete_default_group"}, 400
        db.session.delete(osint_source_group)
        db.session.commit()
        return {"message": f"Successfully deleted {osint_source_group.id}"}, 200

    @classmethod
    def update(cls, osint_source_group_id, data):
        osint_source_group = cls.get(osint_source_group_id)
        if osint_source_group is None:
            return {"error": "OSINT Source Group not found"}, 404

        if name := data.get("name"):
            osint_source_group.name = name

        osint_source_group.description = data.get("description")
        osint_sources = data.get("osint_sources", [])
        osint_source_group.osint_sources = [OSINTSource.get(osint_source) for osint_source in osint_sources]
        word_lists = data.get("word_lists", [])
        osint_source_group.word_lists = [WordList.get(word_list) for word_list in word_lists]
        db.session.commit()
        return {"message": f"Successfully updated {osint_source_group.name}", "id": f"{osint_source_group.id}"}, 201


class OSINTSourceGroupOSINTSource(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="SET NULL"), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="SET NULL"), primary_key=True)


class OSINTSourceGroupWordList(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="SET NULL"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="SET NULL"), primary_key=True)
