from datetime import datetime, timedelta

import uuid as uuid_generator
from sqlalchemy import orm, or_, text, and_
from sqlalchemy.sql.expression import cast
from typing import Any
import sqlalchemy

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.managers.log_manager import logger
from core.model.news_item import NewsItemAggregate
from core.model.report_item_type import AttributeGroupItem
from core.model.report_item_type import ReportItemType
from core.model.acl_entry import ACLEntry
from core.model.user import User
from core.model.acl_entry import ItemType
from core.model.attribute import AttributeType


class ReportItemAttribute(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    binary_description = db.Column(db.String())

    attribute_group_item_id = db.Column(db.Integer, db.ForeignKey("attribute_group_item.id", ondelete="CASCADE"))
    attribute_group_item = db.relationship("AttributeGroupItem")

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=True)
    report_item = db.relationship("ReportItem")

    def __init__(
        self,
        value,
        attribute_group_item_id,
        binary_mime_type=None,
        binary_description=None,
        id=None,
    ):
        self.id = id
        self.value = value
        self.binary_mime_type = binary_mime_type
        self.binary_description = binary_description
        self.attribute_group_item_id = attribute_group_item_id

    @classmethod
    def find_by_attribute_group(cls, attribute_group_id, report_item_id=None):
        return cls.query.filter_by(attribute_group_item_id=attribute_group_id).filter_by(report_item_id=report_item_id).first()

    @classmethod
    def update_values_from_report(cls, report_item_id, attribute_data):
        for attribute_id, data in attribute_data.items():
            if report_item_attribute := cls.get(attribute_id):
                report_item_attribute.value = data["value"]

        db.session.commit()

    @staticmethod
    def sort(report_item_attribute):
        return report_item_attribute.last_updated

    def update(self, new_item: dict[str, Any]) -> int | None:
        for key, value in new_item.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)

        db.session.commit()
        return self.id or None

    def to_report_dict(self):
        data = {
            "value": self.value,
            "attribute_group_item_id": self.attribute_group_item_id,
        }
        if self.binary_mime_type:
            data["binary_mime_type"] = self.binary_mime_type
        if self.binary_description:
            data["binary_description"] = self.binary_description
        return data


class ReportItemRemoteReportItem(BaseModel):
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    remote_report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)


class ReportItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64))

    title = db.Column(db.String())
    title_prefix = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User")
    remote_user = db.Column(db.String())

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), nullable=True)
    report_item_type = db.relationship("ReportItemType")

    news_item_aggregates = db.relationship("NewsItemAggregate", secondary="report_item_news_item_aggregate")

    remote_report_items = db.relationship(
        "ReportItem",
        secondary="report_item_remote_report_item",
        primaryjoin=ReportItemRemoteReportItem.report_item_id == id,
        secondaryjoin=ReportItemRemoteReportItem.remote_report_item_id == id,
    )

    attributes = db.relationship(
        "ReportItemAttribute",
        back_populates="report_item",
        cascade="all, delete-orphan",
    )

    report_item_cpes = db.relationship("ReportItemCpe", cascade="all, delete-orphan")

    def __init__(
        self,
        uuid,
        title,
        title_prefix,
        report_item_type_id,
        news_item_aggregates,
        remote_report_items,
        attributes,
        completed,
        id=None,
    ):
        self.id = id

        self.uuid = uuid or str(uuid_generator.uuid4())
        self.title = title
        self.title_prefix = title_prefix
        self.report_item_type_id = report_item_type_id
        self.attributes = attributes
        self.completed = completed
        self.report_item_cpes = []

        self.news_item_aggregates = [NewsItemAggregate.get(news_item_aggregate.id) for news_item_aggregate in news_item_aggregates]

        self.remote_report_items = [ReportItem.get(remote_report_item.id) for remote_report_item in remote_report_items]

    @classmethod
    def count_all(cls, is_completed):
        return cls.query.filter_by(completed=is_completed).count()

    @classmethod
    def find_by_uuid(cls, report_item_uuid):
        return cls.query.filter_by(uuid=report_item_uuid)

    @classmethod
    def get_json(cls, filter, user):
        reports, count = cls.get_by_filter(filter, user, True)
        items = [report.to_dict() for report in reports]
        return {"total_count": count, "items": items}

    @classmethod
    def get_aggregate_ids(cls, id):
        report_item = cls.query.get(id)
        return [aggregate.id for aggregate in report_item.aggregates]

    @classmethod
    def get_detail_json(cls, id):
        report_item = cls.get(id)
        return report_item.to_detail_dict() if report_item else None

    @classmethod
    def get_groups(cls):
        result = (
            db.session.query(ReportItem.remote_user)
            .distinct()
            .group_by(ReportItem.remote_user)
            .filter(ReportItem.remote_user is not None)
            .all()
        )
        groups = {row[0] for row in result if row[0] is not None}
        return list(groups)

    def to_detail_dict(self):
        data = self.to_dict()
        data["attributes"] = {attribute.id: attribute.to_report_dict() for attribute in self.attributes}
        data["news_item_aggregates"] = [aggregate.to_dict() for aggregate in self.news_item_aggregates if aggregate]
        return data

    @classmethod
    def from_dict(cls, data) -> "ReportItem":
        logger.debug(f"Creating ReportItem from {data}")
        attributes = ReportItemAttribute.load_multiple(data.pop("attributes"))
        return cls(attributes=attributes, **data)

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["ReportItem"]:
        return [cls.from_dict(report_item) for report_item in data]

    @classmethod
    def add(cls, report_item_data, user):
        report_item = cls.from_dict(report_item_data)

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return report_item, 401

        report_item.user_id = user.id
        report_item.update_cpes()
        report_item.add_attributes()

        db.session.add(report_item)
        db.session.commit()

        return report_item, 200

    def add_attributes(self):
        """Adds attributes based on the report item type to the report item."""
        report_item_type = ReportItemType.get(self.report_item_type_id)
        if not report_item_type:
            return
        attribute_groups = report_item_type.attribute_groups
        for attribute_group in attribute_groups:
            for attribute_group_item in attribute_group.attribute_group_items:
                self.attributes.append(ReportItemAttribute(attribute_group_item_id=attribute_group_item.id, value=""))

    @classmethod
    def allowed_with_acl(cls, report_item_id, user, see, access, modify):
        query = db.session.query(ReportItem.id).distinct().group_by(ReportItem.id).filter(ReportItem.id == report_item_id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(
                    ReportItem.uuid == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.REPORT_ITEM,
                ),
                and_(
                    cast(ReportItem.report_item_type_id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE,
                ),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_for_sync(cls, last_synced, report_item_types):
        report_item_type_ids = {report_item_type.id for report_item_type in report_item_types}

        last_sync_time = datetime.now()

        query = cls.query.filter(
            ReportItem.last_updated >= last_synced,
            ReportItem.last_updated <= last_sync_time,
            ReportItem.report_item_type_id.in_(report_item_type_ids),
        )

        report_items = query.all()

        return [report_item.to_dict() for report_item in report_items], last_sync_time

    @classmethod
    def get_by_filter(cls, filter: dict, user, acl_check: bool):
        query = cls.query

        if acl_check:
            query = query.outerjoin(
                ACLEntry,
                and_(
                    ReportItem.uuid == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.REPORT_ITEM,
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        group = filter.get("group")
        if group and group != "":
            query = cls.query.filter(ReportItem.remote_user == group)

        search = filter.get("search")
        if search and search != "":
            query = query.join(ReportItemAttribute, ReportItem.id == ReportItemAttribute.report_item_id).filter(
                or_(
                    ReportItemAttribute.value.ilike(search),
                    ReportItem.title.ilike(search),
                    ReportItem.title_prefix.ilike(search),
                )
            )

        if "completed" in filter and filter["completed"].lower() != "false":
            query = query.filter(ReportItem.completed)

        if "incompleted" in filter and filter["incompleted"].lower() != "false":
            query = query.filter(ReportItem.completed == False)

        if "range" in filter and filter["range"].upper() != "ALL":
            filter_range = filter["range"].upper()
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            if filter_range == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            query = query.filter(ReportItem.created >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(ReportItem.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(ReportItem.created))
        offset = filter.get("offset", 0)
        limit = filter.get("limit", 20)

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def identical(cls, uuid):
        return db.session.query(db.exists().where(ReportItem.uuid == uuid)).scalar()

    @classmethod
    def get_by_cpe(cls, cpes):
        if len(cpes) <= 0:
            return []
        query_string = "SELECT DISTINCT report_item_id FROM report_item_cpe WHERE value LIKE ANY(:cpes) OR {}"
        params = {"cpes": cpes}

        inner_query = ""
        for i in range(len(cpes)):
            if i > 0:
                inner_query += " OR "
            param = f"cpe{str(i)}"
            inner_query += f":{param} LIKE value"
            params[param] = cpes[i]

        result = db.engine.execute(text(query_string.format(inner_query)), params)

        return [row[0] for row in result if row[0] is not None]

    @classmethod
    def add_aggregates(cls, id: int, aggregate_ids: list, user: User) -> tuple[Any, int]:
        report_item = cls.query.get(id)
        if report_item is None:
            return None, 404

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return f"User {user.id} is not allowed to update Report {report_item.id}", 401

        for aggregate_id in aggregate_ids:
            report_item.news_item_aggregates.append(NewsItemAggregate.get(aggregate_id))

        db.session.commit()

        return f"Successfully added {aggregate_ids} to {report_item.id}", 200

    @classmethod
    def set_aggregates(cls, id: int, aggregate_ids: list, user: User) -> tuple[Any, int]:
        report_item = cls.query.get(id)
        if report_item is None:
            return None, 404

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return f"User {user.id} is not allowed to update Report {report_item.id}", 401

        logger.info(f"Setting aggregates: {aggregate_ids} for {report_item.id}")
        aggregates = [NewsItemAggregate.get(aggregate_id) for aggregate_id in aggregate_ids]
        report_item.news_item_aggregates = aggregates

        db.session.commit()

        return f"Successfully added {aggregate_ids} to {report_item.id}", 200

    @classmethod
    def remove_aggregates(cls, id: int, aggregate_ids: list, user: User) -> tuple[Any, int]:
        logger.debug(f"Removing {aggregate_ids} from {id}")
        report_item = cls.query.get(id)
        if report_item is None:
            return None, 404

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return f"User {user.id} is not allowed to update Report {report_item.id}", 401

        for aggregate_id in aggregate_ids:
            report_item.news_item_aggregates.pop(NewsItemAggregate.get(aggregate_id))

        db.session.commit()

        return f"Successfully removed {aggregate_ids} to {report_item.id}", 200

    @classmethod
    def update_report_item(cls, id: int, data: dict, user: User) -> tuple[dict, int]:
        report_item = cls.get(id)
        if report_item is None:
            return {"error": f"No Report with id '{id}' found"}, 404

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return report_item, 401

        report_item.title = data["title"]
        report_item.title_prefix = data["title_prefix"]
        report_item.completed = data["completed"]

        if attributes_data := data.pop("attributes", None):
            ReportItemAttribute.update_values_from_report(report_item.id, attributes_data)

        if "aggregate_ids" in data:
            for aggregate_id in data["aggregate_ids"]:
                aggregate = NewsItemAggregate.get(aggregate_id)
                report_item.news_item_aggregates.append(aggregate)

        db.session.commit()

        return {"message": "Successfully updated Report Item", "id": report_item.id}, 200

    @classmethod
    def get_updated_data(cls, id, data):
        report_item = cls.query.get(id)
        if report_item is not None:
            if "update" in data:
                if "title" in data:
                    data["title"] = report_item.title

                if "title_prefix" in data:
                    data["title_prefix"] = report_item.title_prefix

                if "completed" in data:
                    data["completed"] = report_item.completed

                if "attribute_id" in data:
                    for attribute in report_item.attributes:
                        if attribute.id == data["attribute_id"]:
                            data["attribute_value"] = attribute.value
                            data["attribute_last_updated"] = attribute.last_updated.isoformat()
                            break

            if "add" in data:
                if "aggregate_ids" in data:
                    data["news_item_aggregates"] = []
                    for aggregate_id in data["aggregate_ids"]:
                        if aggregate := NewsItemAggregate.get(aggregate_id):
                            data["news_item_aggregates"].append(aggregate.to_dict())

                if "remote_report_item_ids" in data:
                    data["remote_report_items"] = []
                    for remote_report_item_id in data["remote_report_item_ids"]:
                        remote_report_item = ReportItem.get(remote_report_item_id)
                        if remote_report_item is not None:
                            data["remote_report_items"].append(remote_report_item.to_dict())

                if "attribute_id" in data:
                    for attribute in report_item.attributes:
                        if attribute.id == data["attribute_id"]:
                            data["attribute_value"] = attribute.value
                            data["binary_mime_type"] = attribute.binary_mime_type
                            data["binary_description"] = attribute.binary_description
                            data["attribute_last_updated"] = attribute.last_updated.isoformat()
                            break

        return data

    @classmethod
    def add_attachment(cls, id, attribute_group_item_id, user, file, description):
        report_item = cls.query.get(id)
        file_data = file.read()
        new_attribute = ReportItemAttribute(
            value=file.filename,
            binary_description=file.filename,
            binary_mime_type=file.mimetype,
            attribute_group_item_id=attribute_group_item_id,
        )

        new_attribute.binary_data = file_data
        report_item.attributes.append(new_attribute)

        report_item.last_updated = datetime.now()

        data = {
            "add": True,
            "user_id": user.id,
            "report_item_id": int(id),
            "attribute_id": new_attribute.id,
        }
        db.session.commit()

        return data

    @classmethod
    def remove_attachment(cls, id, attribute_id, user):
        report_item = cls.query.get(id)
        attribute_to_delete = None
        for attribute in report_item.attributes:
            if attribute.id == attribute_id:
                attribute_to_delete = attribute
                break

        if attribute_to_delete is not None:
            report_item.attributes.remove(attribute_to_delete)

        report_item.last_updated = datetime.now()

        data = {
            "delete": True,
            "user_id": user.id,
            "report_item_id": int(id),
            "attribute_id": attribute_id,
        }
        db.session.commit()

        return data

    def update_cpes(self):
        self.report_item_cpes = []
        if self.completed:
            for attribute in self.attributes:
                attribute_group = AttributeGroupItem.get(attribute.attribute_group_item_id)
                if not attribute_group:
                    continue
                if attribute_group.attribute.type == AttributeType.CPE:
                    self.report_item_cpes.append(ReportItemCpe(attribute.value))

    @classmethod
    def add_remote_report_items(cls, report_item_data, remote_node_name):
        report_items = ReportItem.load_multiple(report_item_data)

        for report_item in report_items:
            original_report_item = cls.find_by_uuid(report_item.uuid)
            if original_report_item is None:
                report_item.remote_user = remote_node_name
                db.session.add(report_item)
            else:
                original_report_item.title = report_item.title
                original_report_item.title_prefix = report_item.title_prefix
                original_report_item.completed = report_item.completed
                original_report_item.last_updated = datetime.now()
                original_report_item.attributes = report_item.attributes

        db.session.commit()


class ReportItemCpe(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"))
    report_item = db.relationship("ReportItem")

    def __init__(self, value):
        self.id = None
        self.value = value
