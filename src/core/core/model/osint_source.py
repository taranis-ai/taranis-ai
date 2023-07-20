import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import or_, and_

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.acl_entry import ACLEntry, ItemType
from core.model.collector import Collector
from core.model.parameter_value import ParameterValue
from core.model.word_list import WordList
from core.model.base_model import BaseModel
from core.model.queue import ScheduleEntry


class OSINTSource(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    collector_id = db.Column(db.String, db.ForeignKey("collector.id"))
    parameter_values = db.relationship("ParameterValue", secondary="osint_source_parameter_value", cascade="all, delete")

    word_lists = db.relationship("WordList", secondary="osint_source_word_list")

    modified = db.Column(db.DateTime, default=datetime.now)
    last_collected = db.Column(db.DateTime, default=None)
    last_attempted = db.Column(db.DateTime, default=None)
    state = db.Column(db.SmallInteger, default=0)
    last_error_message = db.Column(db.String, default=None)

    def __init__(self, name, description, collector_id, parameter_values, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.collector_id = collector_id
        self.parameter_values = parameter_values

        self.word_lists = []
        if word_lists:
            self.word_lists.extend(WordList.get(word_list.id) for word_list in word_lists)

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
            query = query.join(Collector, OSINTSource.collector_id == Collector.id).filter(
                or_(
                    OSINTSource.name.ilike(search_string),
                    OSINTSource.description.ilike(search_string),
                    Collector.type.ilike(search_string),
                )
            )

        return query.order_by(db.asc(OSINTSource.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        sources, count = cls.get_by_filter(search)
        items = [source.to_dict() for source in sources]
        return {"total_count": count, "items": items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OSINTSource":
        drop_keys = ["tag", "modified", "last_collected", "last_attempted", "state", "last_error_message"]
        [data.pop(key, None) for key in drop_keys if key in data]

        parameter_values = [ParameterValue.from_dict(parameter_value) for parameter_value in data.pop("parameter_values", [])]
        collector_type = None
        if "collector" in data:
            collector_type = data.pop("collector")["type"]
        elif "collector_type" in data:
            collector_type = data.pop("collector_type")
        if collector_type:
            collector = Collector.find_by_type(collector_type)
            if not collector:
                logger.error(f"Collector {collector_type} not found")
                raise ValueError(f"Collector {collector_type} not found")
            collector_id = collector.id
        else:
            collector_id = data.pop("collector_id")
        return cls(parameter_values=parameter_values, collector_id=collector_id, **data)

    def to_dict(self):
        data = super().to_dict()
        data["word_lists"] = [word_list.id for word_list in self.word_lists]
        data["parameter_values"] = [parameter_value.to_dict() for parameter_value in self.parameter_values]
        data["tag"] = "mdi-animation-outline"
        return data

    def to_task_id(self):
        return f"osint_source_{self.id}_{self.collector.type}"

    def get_schedule(self):
        return ParameterValue.find_param_value(self.parameter_values, "REFRESH_INTERVAL") or "10"

    def to_task_dict(self):
        return {"id": self.to_task_id(), "task": "worker.tasks.collect", "schedule": self.get_schedule(), "args": [self.id]}

    def to_export_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "collector_type": self.collector.type,
            "parameter_values": [parameter_value.to_export_dict() for parameter_value in self.parameter_values],
        }

    @classmethod
    def get_all_with_type(cls):
        sources, count = cls.get_by_filter(None)
        items = [source.to_list() for source in sources]
        return {"total_count": count, "items": items}

    def to_list(self):
        return {"id": self.id, "name": self.name, "description": self.description, "collector_type": self.collector.type}

    def to_collector_dict(self):
        data = super().to_dict()
        data["parameter_values"] = {parameter_value.parameter.key: parameter_value.value for parameter_value in self.parameter_values}
        data["type"] = Collector.get_type(self.collector_id)
        return data

    @classmethod
    def get_all_by_type(cls, collector_type: str):
        query = cls.query.join(Collector, OSINTSource.collector_id == Collector.id).filter(Collector.type == collector_type)
        sources = query.order_by(db.nulls_first(db.asc(OSINTSource.last_collected)), db.nulls_first(db.asc(OSINTSource.last_attempted))).all()
        return [source.to_collector_dict() for source in sources]

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

        for value in osint_source.parameter_values:
            for updated_value in updated_osint_source.parameter_values:
                if value.parameter_key == updated_value.parameter_key:
                    value.value = updated_value.value

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
        if error_message is None:
            self.last_collected = datetime.now()
            self.state = 0
        else:
            logger.error(f"Updating status for {self.id} with error message {error_message}")
            self.state = 1
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

    osint_sources = db.relationship("OSINTSource", secondary="osint_source_group_osint_source")
    word_lists = db.relationship("WordList", secondary="osint_source_group_word_list")

    def __init__(self, name, description, osint_sources=None, default=False, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.default = default
        self.osint_sources = [OSINTSource.get(osint_source) for osint_source in osint_sources] if osint_sources else []
        self.word_lists = [WordList.get(word_list.id) for word_list in word_lists] if word_lists else []

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
