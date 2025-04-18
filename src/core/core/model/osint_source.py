import uuid
import json
import base64
from datetime import datetime
from typing import Any, Sequence, TYPE_CHECKING
from sqlalchemy.orm import deferred, Mapped, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.managers import schedule_manager
from core.log import logger
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.parameter_value import ParameterValue
from core.model.word_list import WordList
from core.model.base_model import BaseModel
from core.model.settings import Settings
from core.model.worker import COLLECTOR_TYPES, Worker
from core.model.role import TLPLevel
from core.service.role_based_access import RoleBasedAccessService, RBACQuery
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from core.model.user import User
    from core.model.news_item import NewsItem


class OSINTSource(BaseModel):
    __tablename__ = "osint_source"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    type: Mapped[COLLECTOR_TYPES] = db.Column(db.Enum(COLLECTOR_TYPES))
    parameters: Mapped[list["ParameterValue"]] = relationship(
        "ParameterValue", secondary="osint_source_parameter_value", cascade="all, delete"
    )
    groups: Mapped[list["OSINTSourceGroup"]] = relationship("OSINTSourceGroup", secondary="osint_source_group_osint_source")

    icon: Any = deferred(db.Column(db.LargeBinary))
    state: Mapped[int] = db.Column(db.SmallInteger, default=-1)
    last_collected: Mapped[datetime] = db.Column(db.DateTime, default=None)
    last_attempted: Mapped[datetime] = db.Column(db.DateTime, default=None)
    last_error_message: Mapped[str | None] = db.Column(db.String, default=None, nullable=True)
    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem", back_populates="osint_source")

    def __init__(self, name: str, description: str, type: str | COLLECTOR_TYPES, parameters=None, icon=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type if isinstance(type, COLLECTOR_TYPES) else COLLECTOR_TYPES(type.lower())
        if icon is not None and (icon_data := self.is_valid_base64(icon)):
            self.icon = icon_data

        self.parameters = Worker.parse_parameters(self.type, parameters)

    @property
    def tlp_level(self) -> TLPLevel:
        if value := ParameterValue.find_value_by_parameter(self.parameters, "TLP_LEVEL"):
            return TLPLevel(value)
        return TLPLevel(Settings.get_settings().get("default_tlp_level", TLPLevel.CLEAR.value))

    @classmethod
    def get_all_for_collector(cls) -> Sequence["OSINTSource"]:
        return (
            db.session.execute(
                db.select(cls)
                .where(cls.type != COLLECTOR_TYPES.MANUAL_COLLECTOR)
                .where(cls.state != -2)
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
            query = query.where(db.or_(cls.name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%"), cls.type.ilike(f"%{search}%")))

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

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters if parameter.value}
        data["icon"] = base64.b64encode(self.icon).decode("utf-8") if self.icon else None
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("icon", None)
        data["word_lists"] = []
        for group in self.groups:
            data["word_lists"].extend([word_list.to_dict() for word_list in group.word_lists if word_list])
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters if parameter.value}
        return data

    def to_assess_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "icon": base64.b64encode(self.icon).decode("utf-8") if self.icon else None,
            "name": self.name,
            "type": self.type,
        }

    def to_task_id(self) -> str:
        return f"{self.type}_{self.id}"

    def get_schedule(self) -> str:
        if refresh_interval := ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL"):
            return refresh_interval

        # use default interval (0 */8 * * * = 8h) if no REFERESH_INTERVAL was set will be moved to admin settings
        logger.info(f"REFRESH_INTERVAL for source {self.id} set to default value (8 hours)")
        return "0 */8 * * *"

    def to_task_dict(self, crontab_str: str):
        return {
            "id": self.to_task_id(),
            "name": f"{self.type}_{self.name}",
            "jobs_params": {
                "trigger": CronTrigger.from_crontab(crontab_str),
                "max_instances": 1,
            },
            "celery": {
                "name": "collector_task",
                "args": [self.id],
                "queue": "collectors",
                "task_id": self.to_task_id(),
            },
        }

    @classmethod
    def add(cls, data):
        osint_source = cls.from_dict(data)
        db.session.add(osint_source)
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    @classmethod
    def toggle_state(cls, source_id: str, state: str) -> tuple[dict, int]:
        osint_source = cls.get(source_id)
        if not osint_source:
            return {"error": f"OSINT Source with ID: {source_id} not found"}, 404

        if state == "enable":
            osint_source.state = -1
        elif state == "disable":
            osint_source.state = -2
        else:
            return {"error": "Invalid state"}, 400

        db.session.commit()
        return {"message": f"OSINT Source {osint_source.name} state toggled", "id": f"{source_id}", "state": osint_source.state}, 200

    @classmethod
    def update(cls, osint_source_id: str, data: dict) -> "OSINTSource|None":
        osint_source = cls.get(osint_source_id)
        if not osint_source:
            return None
        if name := data.get("name"):
            osint_source.name = name
        if description := data.get("description"):
            osint_source.description = description
        icon_str = data.get("icon")
        if icon_str is not None and (icon := osint_source.is_valid_base64(icon_str)):
            osint_source.icon = icon
        if parameters := data.get("parameters"):
            update_parameter = ParameterValue.get_or_create_from_list(parameters)
            osint_source.parameters = ParameterValue.get_update_values(osint_source.parameters, update_parameter)
        db.session.commit()
        osint_source.schedule_osint_source()
        return osint_source

    def update_parameters(self, parameters: dict[str, Any]):
        update_parameter = ParameterValue.get_or_create_from_list(parameters)
        self.parameters = ParameterValue.get_update_values(self.parameters, update_parameter)
        db.session.commit()

    @classmethod
    def delete(cls, source_id: str, force: bool = False) -> tuple[dict, int]:
        if not (source := cls.get(source_id)):
            return {"error": f"OSINT Source with ID: {source_id} not found"}, 404

        try:
            source.unschedule_osint_source()
            db.session.delete(source)
            db.session.commit()
            return {"message": f"OSINT Source {source.name} deleted", "id": f"{source_id}"}, 200
        except IntegrityError as e:
            logger.warning(f"IntegrityError: {e.orig}")
            return {"error": f"Deleting OSINT Source with ID: {source_id} failed {str(e)}"}, 500

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
        if self.type == COLLECTOR_TYPES.MANUAL_COLLECTOR:
            return {"message": "Manual collector does not need to be scheduled"}, 200

        interval = self.get_schedule()
        entry = self.to_task_dict(interval)
        schedule_manager.schedule.add_celery_task(entry)

        logger.info(f"Schedule for source {self.id} updated with - {entry}")
        return {"message": f"Schedule for source {self.id} updated"}, 200

    def unschedule_osint_source(self):
        entry_id = self.to_task_id()
        schedule_manager.schedule.remove_periodic_task(entry_id)
        logger.info(f"Schedule for source {self.id} removed")
        return {"message": f"Schedule for source {self.id} removed"}, 200

    def to_export_dict(self, id_to_index_map: dict, export_args: dict) -> dict[str, Any]:
        export_dict = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "parameters": self.get_export_parameters(export_args.get("with_secrets", False)),
        }
        # test if source is in a group that is not default
        if export_args.get("with_groups", False) and any(group for group in self.groups if not group.default):
            export_dict["group_idx"] = id_to_index_map.get(self.id)

        return export_dict

    @classmethod
    def export_osint_sources(cls, export_args: dict | None = None) -> bytes:
        export_args = export_args or {}
        query = db.select(cls).where(cls.type != COLLECTOR_TYPES.MANUAL_COLLECTOR)
        if source_ids := export_args.get("source_ids", False):
            query = query.filter(cls.id.in_(source_ids))

        data = cls.get_filtered(query)
        if not data:
            return json.dumps({"error": "no sources found"}).encode("utf-8")

        id_to_index_map = {osint_source.id: idx for idx, osint_source in enumerate(data, 1)}
        export_data = {
            "version": 3,
            "sources": [osint_source.to_export_dict(id_to_index_map, export_args) for osint_source in data],
        }
        if export_args.get("with_groups", False):
            groups = OSINTSourceGroup.get_all_without_default() or []
            export_data["groups"] = [group.to_export_dict(id_to_index_map) for group in groups]

        logger.debug(f"Exporting {len(export_data['sources'])} sources")
        return json.dumps(export_data).encode("utf-8")

    def get_export_parameters(self, with_secrets: bool = False) -> list[dict[str, str]]:
        parameters = []
        for parameter in self.parameters:
            if not with_secrets and parameter.parameter == "PROXY_SERVER" and parameter.value:
                parameters.append({parameter.parameter: "<REDACTED>"})
                continue
            if parameter.value:
                parameters.append(parameter.to_dict())
        return parameters

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
    def add_multiple_with_group(cls, sources, groups) -> list[str]:
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
    def import_osint_sources(cls, file) -> list[str]:
        file_data = file.read()
        json_data = json.loads(file_data.decode("utf8"))
        groups = []
        if json_data["version"] == 1:
            data = cls.parse_version_1(json_data["data"])
        elif json_data["version"] == 2:
            data = json_data["data"]
        elif json_data["version"] == 3:
            data = json_data["sources"]
            groups = json_data.get("groups", [])
        else:
            raise ValueError("Unsupported version")

        ids = cls.add_multiple_with_group(data, groups)
        logger.debug(f"Imported {len(ids)} sources")
        return ids

    @classmethod
    def get_all_for_assess_api(cls, user=None) -> tuple[dict[str, Any], int]:
        filter_args = {}
        if user:
            query = cls.get_filter_query_with_acl(filter_args, user)
        else:
            query = cls.get_filter_query(filter_args)
        if items := cls.get_filtered(query):
            return {"items": [item.to_assess_dict() for item in items]}, 200

        return {"items": []}, 200

    @classmethod
    def delete_all(cls) -> tuple[dict[str, Any], int]:
        # Clear the association table entries
        db.session.execute(db.delete(OSINTSourceGroupOSINTSource).where(OSINTSourceGroupOSINTSource.osint_source_id.in_(db.select(cls.id))))

        # Delete all rows from the OSINTSource table
        db.session.execute(db.delete(cls))
        db.session.commit()
        logger.debug(f"All {cls.__name__} deleted")
        return {"message": f"All {cls.__name__} deleted"}, 200


class OSINTSourceParameterValue(BaseModel):
    osint_source_id: Mapped[str] = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("parameter_value.id", ondelete="CASCADE"), primary_key=True)


class OSINTSourceGroup(BaseModel):
    __tablename__ = "osint_source_group"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    default: Mapped[bool] = db.Column(db.Boolean(), default=False)

    osint_sources: Mapped[list["OSINTSource"]] = relationship(
        "OSINTSource",
        secondary="osint_source_group_osint_source",
        back_populates="groups",
    )
    word_lists: Mapped[list["WordList"]] = relationship("WordList", secondary="osint_source_group_word_list")

    def __init__(self, name, description="", osint_sources=None, default=False, word_lists=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.default = default
        self.osint_sources = OSINTSource.get_bulk(osint_sources or []) or []
        self.word_lists = WordList.get_bulk(word_lists or [])

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
            query = query.where(db.or_(cls.name.ilike(f"%{search}%"), cls.description.ilike(f"%{search}%")))

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
        if default_group := cls.get_default():
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

    def allowed_with_acl(self, user: "User | None", require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(
            user=user, resource_id=self.id, resource_type=ItemType.OSINT_SOURCE_GROUP, require_write_access=require_write_access
        )

        return RoleBasedAccessService.user_has_access_to_resource(query)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["osint_sources"] = [osint_source.id for osint_source in self.osint_sources if osint_source]
        data["word_lists"] = [word_list.id for word_list in self.word_lists if word_list]
        return data

    @classmethod
    def delete(cls, osint_source_group_id: str, user: "User | None" = None) -> tuple[dict, int]:
        osint_source_group = cls.get(osint_source_group_id)
        if not osint_source_group:
            return {"message": "No Sourcegroup found"}, 404
        if osint_source_group.default is True:
            return {"message": "could_not_delete_default_group"}, 400

        if not osint_source_group.allowed_with_acl(user=user, require_write_access=True):
            return {"error": "User not allowed to update this group"}, 403

        db.session.delete(osint_source_group)
        db.session.commit()
        return {"message": f"Successfully deleted {osint_source_group.id}"}, 200

    @classmethod
    def update(cls, osint_source_group_id: str, data: dict, user: "User | None" = None) -> tuple[dict, int]:
        osint_source_group = cls.get(osint_source_group_id)
        if osint_source_group is None:
            return {"error": "OSINT Source Group not found"}, 404

        if not osint_source_group.allowed_with_acl(user=user, require_write_access=True):
            return {"error": "User not allowed to update this group"}, 403

        if name := data.get("name"):
            osint_source_group.name = name

        if description := data.get("description"):
            osint_source_group.description = description
        osint_sources = data.get("osint_sources", [])
        osint_source_group.osint_sources = OSINTSource.get_bulk(osint_sources)
        word_lists = data.get("word_lists", [])
        osint_source_group.word_lists = WordList.get_bulk(word_lists)
        db.session.commit()
        return {"message": f"Successfully updated {osint_source_group.name}", "id": f"{osint_source_group.id}"}, 201

    def to_assess_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
        }

    @classmethod
    def get_all_for_assess_api(cls, user=None) -> tuple[dict[str, Any], int]:
        filter_args = {}
        if user:
            query = cls.get_filter_query_with_acl(filter_args, user)
        else:
            query = cls.get_filter_query(filter_args)
        if items := cls.get_filtered(query):
            return {"items": [item.to_assess_dict() for item in items]}, 200

        return {"items": []}, 404


class OSINTSourceGroupOSINTSource(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="SET NULL"), primary_key=True)
    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id", ondelete="SET NULL"), primary_key=True)


class OSINTSourceGroupWordList(BaseModel):
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id", ondelete="SET NULL"), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="SET NULL"), primary_key=True)
