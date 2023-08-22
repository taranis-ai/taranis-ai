import uuid
import json
from datetime import datetime
from typing import Any
from sqlalchemy import or_, and_

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.acl_entry import ACLEntry, ItemType
from core.model.parameter_value import ParameterValue
from core.model.word_list import WordList
from core.model.base_model import BaseModel
from core.model.queue import ScheduleEntry
from core.model.worker import COLLECTOR_TYPES, Worker


class OSINTSource(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.Enum(COLLECTOR_TYPES))
    parameters = db.relationship("ParameterValue", secondary="osint_source_parameter_value", cascade="all, delete")

    word_lists = db.relationship("WordList", secondary="osint_source_word_list")
    groups = db.relationship("OSINTSourceGroup", secondary="osint_source_group_osint_source")

    state = db.Column(db.SmallInteger, default=0)
    last_collected = db.Column(db.DateTime, default=None)
    last_attempted = db.Column(db.DateTime, default=None)
    last_error_message = db.Column(db.String, default=None)

    def __init__(self, name, description, type, parameters=None, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = ParameterValue.get_or_create_from_list(parameters=parameters) if parameters else Worker.get_parameters(type)
        self.word_lists = [WordList.get(word_list) for word_list in word_lists] if word_lists else []

    @classmethod
    def get_all(cls) -> list["OSINTSource"]:
        return cls.query.order_by(
            db.nulls_first(db.asc(OSINTSource.last_collected)), db.nulls_first(db.asc(OSINTSource.last_attempted))
        ).all()

    @classmethod
    def get_by_filter(cls, search=None):
        query = cls.query

        if search:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    OSINTSource.name.ilike(search_string),
                    OSINTSource.description.ilike(search_string),
                    OSINTSource.type.ilike(search_string),
                ).distinct()
            )

        return query.order_by(db.asc(OSINTSource.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        sources, count = cls.get_by_filter(search)
        items = [source.to_dict() for source in sources]
        return {"total_count": count, "items": items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OSINTSource":
        drop_keys = ["last_collected", "last_attempted", "state", "last_error_message"]
        [data.pop(key, None) for key in drop_keys if key in data]
        return cls(**data)

    def to_dict(self):
        data = super().to_dict()
        data["word_lists"] = [word_list.id for word_list in self.word_lists if word_list]
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    def to_worker_dict(self):
        data = super().to_dict()
        data["word_lists"] = [word_list.to_dict() for word_list in self.word_lists if word_list]
        for group in self.groups:
            data["word_lists"].extend([word_list.to_dict() for word_list in group.word_lists])
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    def to_task_id(self):
        return f"osint_source_{self.id}_{self.type}"

    def get_schedule(self):
        refresh_interval = [parameter.value for parameter in self.parameters if parameter.parameter == "REFRESH_INTERVAL"]
        return refresh_interval[0] if len(refresh_interval) == 1 else "60"

    def to_task_dict(self):
        return {"id": self.to_task_id(), "task": "worker.tasks.collect", "schedule": self.get_schedule(), "args": [self.id]}

    def to_export_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }

    @classmethod
    def get_all_with_type(cls):
        sources, count = cls.get_by_filter(None)
        items = [source.to_list() for source in sources]
        return {"total_count": count, "items": items}

    def to_list(self):
        return {"id": self.id, "name": self.name, "description": self.description, "type": self.type}

    @classmethod
    def get_all_by_type(cls, collector_type: str):
        query = cls.query.filter(OSINTSource.type == collector_type)
        sources = query.order_by(db.nulls_first(db.asc(OSINTSource.last_collected)), db.nulls_first(db.asc(OSINTSource.last_attempted))).all()
        return [source.to_dict() for source in sources]

    @classmethod
    def add(cls, data):
        osint_source = cls.from_dict(data)
        db.session.add(osint_source)
        OSINTSourceGroup.add_source_to_default(osint_source)
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    @classmethod
    def update(cls, osint_source_id, data):
        osint_source = cls.query.get(osint_source_id)
        updated_osint_source = cls.from_dict(data)
        osint_source.name = updated_osint_source.name
        osint_source.description = updated_osint_source.description
        osint_source.parameters = updated_osint_source.parameters
        osint_source.word_lists = updated_osint_source.word_lists
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    @classmethod
    def delete(cls, id) -> tuple[str, int]:
        if source := cls.get(id):
            source.unschedule_osint_source()
            db.session.delete(source)
            db.session.commit()
            return f"{cls.__name__} {id} deleted", 200

        return f"{cls.__name__} {id} not found", 404

    def update_status(self, error_message=None):
        self.last_attempted = datetime.now()
        if error_message:
            logger.error(f"Updating status for {self.id} with error message {error_message}")
            self.state = 1
        else:
            self.last_collected = datetime.now()
            self.state = 0
        self.last_error_message = error_message
        db.session.commit()

    def schedule_osint_source(self):
        entry = self.to_task_dict()
        ScheduleEntry.add_or_update(entry)
        logger.info(f"Schedule for source {self.id} updated")
        return {"message": f"Schedule for source {self.id} updated"}, 200

    def unschedule_osint_source(self):
        entry_id = self.to_task_dict()["id"]
        ScheduleEntry.delete(entry_id)
        logger.info(f"Schedule for source {self.id} removed")
        return {"message": f"Schedule for source {self.id} removed"}, 200

    @classmethod
    def export_osint_sources(cls, source_ids=None):
        if source_ids:
            data = cls.query.filter(cls.id.in_(source_ids)).all()  # type: ignore
        else:
            data = cls.get_all()
        for osint_source in data:
            osint_source = osint_source.cleanup_paramaters()
        export_data = {"version": 2, "data": [osint_source.to_export_dict() for osint_source in data]}
        return json.dumps(export_data).encode("utf-8")

    def cleanup_paramaters(self) -> "OSINTSource":
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
    def import_osint_sources(cls, file):
        file_data = file.read()
        json_data = json.loads(file_data.decode("utf8"))
        if json_data["version"] == 1:
            data = cls.parse_version_1(json_data["data"])
        elif json_data["version"] == 2:
            data = json_data["data"]
        else:
            raise ValueError("Unsupported version")
        return cls.add_multiple(data)


class OSINTSourceParameterValue(BaseModel):
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id", ondelete="CASCADE"), primary_key=True)


class OSINTSourceWordList(BaseModel):
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="CASCADE"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="CASCADE"), primary_key=True)


class OSINTSourceGroup(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    default = db.Column(db.Boolean(), default=False)

    osint_sources = db.relationship("OSINTSource", secondary="osint_source_group_osint_source", back_populates="groups")
    word_lists = db.relationship("WordList", secondary="osint_source_group_word_list")

    def __init__(self, name, description, osint_sources=None, default=False, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.default = default
        self.osint_sources = [OSINTSource.get(osint_source) for osint_source in osint_sources] if osint_sources else []
        self.word_lists = [WordList.get(word_list) for word_list in word_lists] if word_lists else []

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(OSINTSourceGroup.name)).all()

    @classmethod
    def get_for_osint_source(cls, osint_source_id):
        return cls.query.join(
            OSINTSourceGroupOSINTSource,
            and_(
                OSINTSourceGroupOSINTSource.osint_source_id == osint_source_id,
                OSINTSourceGroup.id == OSINTSourceGroupOSINTSource.osint_source_group_id,
            ),
        ).all()

    def to_word_list_dict(self):
        flat_entry_list = []
        word_list_entries = [word_list.to_entry_dict() for word_list in self.word_lists if word_list]
        for sublist in word_list_entries:
            flat_entry_list.extend(sublist)
        return flat_entry_list, 200

    @classmethod
    def get_default(cls):
        return cls.query.filter(OSINTSourceGroup.default).first()

    @classmethod
    def add_source_to_default(cls, osint_source: OSINTSource):
        default_group = cls.get_default()
        default_group.osint_sources.append(osint_source)
        db.session.commit()

    @classmethod
    def allowed_with_acl(cls, group_id, user, see: bool, access: bool, modify: bool) -> bool:
        query = db.session.query(OSINTSourceGroup.id).distinct().group_by(OSINTSourceGroup.id).filter(OSINTSourceGroup.id == group_id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                OSINTSourceGroup.id == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.OSINT_SOURCE_GROUP,
            ),
        )
        query = ACLEntry.apply_query(query, user, see, access, modify)
        acl_check_result = query.scalar() is not None
        logger.log_debug(f"ACL Check for {group_id} results: {acl_check_result}")

        return acl_check_result

    @classmethod
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(OSINTSourceGroup.id)

        if acl_check:
            query = query.outerjoin(
                ACLEntry, and_(OSINTSourceGroup.id == ACLEntry.item_id, ACLEntry.item_type == ItemType.OSINT_SOURCE_GROUP)
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search:
            query = query.filter(
                or_(
                    OSINTSourceGroup.name.ilike(f"%{search}%"),
                    OSINTSourceGroup.description.ilike(f"%{search}%"),
                )
            )

        return (
            query.all(),
            query.count(),
        )

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        groups, count = cls.get_by_filter(search, user, acl_check)
        items = [group.to_dict() for group in groups]
        return {"total_count": count, "items": items}

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
        osint_source_group = cls.query.get(osint_source_group_id)
        if osint_source_group is None:
            return "OSINT Source Group not found", 404
        osint_source_group.name = data["name"]
        osint_source_group.description = data["description"]
        osint_source_group.osint_sources = [OSINTSource.get(osint_source) for osint_source in data.pop("osint_sources", [])]
        osint_source_group.word_lists = [WordList.get(word_list) for word_list in data.pop("word_lists", [])]
        db.session.commit()
        return f"Succussfully updated {osint_source_group.id}", 201

        # TODO: Reassign news items to default group
        # if sources_in_default_group is not None:
        #     default_group = osint_source.OSINTSourceGroup.get_default()
        #     for source in sources_in_default_group:
        #         NewsItemAggregate.reassign_to_new_groups(source.id, default_group.id)


class OSINTSourceGroupOSINTSource(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="CASCADE"), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="CASCADE"), primary_key=True)


class OSINTSourceGroupWordList(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="CASCADE"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="CASCADE"), primary_key=True)
