from datetime import datetime, timedelta

import uuid as uuid_generator
from sqlalchemy import orm, or_, text, and_
from sqlalchemy.sql.expression import cast
from typing import Any, Optional
import sqlalchemy

from core.managers.db_manager import db
from core.model.base_model import BaseModel
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
            "title": self.attribute_group_item.title,
        }
        if self.binary_mime_type:
            data["binary_mime_type"] = self.binary_mime_type
        if self.binary_description:
            data["binary_description"] = self.binary_description
        return data


class ReportItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64))

    title = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user = db.relationship("User")

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), nullable=True)
    report_item_type = db.relationship("ReportItemType")

    news_item_aggregates = db.relationship("NewsItemAggregate", secondary="report_item_news_item_aggregate")

    attributes = db.relationship(
        "ReportItemAttribute",
        back_populates="report_item",
        cascade="all, delete-orphan",
    )

    report_item_cpes = db.relationship("ReportItemCpe", cascade="all, delete-orphan", back_populates="report_item")

    def __init__(
        self,
        uuid,
        title,
        report_item_type_id,
        news_item_aggregates,
        attributes=attributes or [],
        completed=False,
        id=None,
    ):
        self.id = id
        self.uuid = uuid or str(uuid_generator.uuid4())
        self.title = title
        self.report_item_type_id = report_item_type_id
        self.attributes = attributes
        self.completed = completed
        self.report_item_cpes = []

        self.news_item_aggregates = [NewsItemAggregate.get(news_item_aggregate.id) for news_item_aggregate in news_item_aggregates]

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
        return [aggregate.id for aggregate in report_item.news_item_aggregates]

    @classmethod
    def get_detail_json(cls, id):
        report_item = cls.get(id)
        return report_item.to_detail_dict() if report_item else None

    def to_dict(self):
        data = super().to_dict()
        data["stories"] = len(self.news_item_aggregates)
        return data

    def to_detail_dict(self):
        data = super().to_dict()
        data["attributes"] = {attribute.id: attribute.to_report_dict() for attribute in self.attributes} if self.attributes else {}
        data["news_item_aggregates"] = [aggregate.to_dict() for aggregate in self.news_item_aggregates if aggregate]
        return data

    @classmethod
    def from_dict(cls, data) -> "ReportItem":
        data["attributes"] = ReportItemAttribute.load_multiple(data.pop("attributes", []))
        return cls(**data)

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["ReportItem"]:
        return [cls.from_dict(report_item) for report_item in data]

    @classmethod
    def add(cls, report_item_data, user):
        report_item = cls.from_dict(report_item_data)

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return report_item, 403

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

        if search := filter.get("search"):
            query = query.join(ReportItemAttribute, ReportItem.id == ReportItemAttribute.report_item_id).filter(
                or_(ReportItemAttribute.value.ilike(f"%{search}%"), ReportItem.title.ilike(f"%{search}%"))
            )

        if "completed" in filter and filter["completed"].lower() != "false":
            query = query.filter(ReportItem.completed)

        if "incompleted" in filter and filter["incompleted"].lower() != "false":
            query = query.filter(ReportItem.completed == False)  # noqa

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
    def get_report_item_and_check_permission(cls, id: int, user: User) -> tuple[Optional["ReportItem"], dict, int]:
        report_item = cls.get(id)
        if not report_item:
            return None, {"error": "Report Item not Found"}, 404

        if not ReportItemType.allowed_with_acl(report_item.report_item_type_id, user, False, False, True):
            return None, {"error": f"User {user.id} is not allowed to update Report {report_item.id}"}, 403

        return report_item, {}, 200

    @classmethod
    def add_aggregates(cls, id: int, item_ids: list[int], user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(id, user)
        if err or not report_item:
            return err, status

        items = [NewsItemAggregate.get(item_id) for item_id in item_ids]
        report_item.news_item_aggregates.extend(items)
        db.session.commit()

        return {"message": f"Successfully added {item_ids} to {report_item.id}"}, 200

    @classmethod
    def remove_aggregates(cls, id: int, aggregate_ids: list[int], user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(id, user)
        if err or not report_item:
            return err, status

        items = [NewsItemAggregate.get(item_id) for item_id in aggregate_ids]
        report_item.news_item_aggregates = [item for item in report_item.news_item_aggregates if item not in items]
        db.session.commit()

        return {"message": f"Successfully removed {aggregate_ids} from {report_item.id}"}, 200

    @classmethod
    def set_aggregates(cls, id: int, aggregate_ids: list, user: User) -> tuple[dict, int]:
        return cls.update_report_item(id, {"aggregate_ids": aggregate_ids}, user)

    @classmethod
    def update_report_item(cls, id: int, data: dict, user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(id, user)
        if err or not report_item:
            return err, status

        if title := data.get("title"):
            report_item.title = title

        completed = data.get("completed")
        if completed is not None:
            report_item.completed = completed

        if attributes_data := data.pop("attributes", None):
            ReportItemAttribute.update_values_from_report(report_item.id, attributes_data)

        if aggregate_ids := data.get("aggregate_ids"):
            report_item.news_item_aggregates = [NewsItemAggregate.get(aggregate_id) for aggregate_id in aggregate_ids]

        db.session.commit()

        return {"message": "Successfully updated Report Item", "id": report_item.id}, 200

    @classmethod
    def add_attachment(cls, id, attribute_group_item_id, user, file) -> tuple[dict, int]:
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

        db.session.commit()

        return {"message": "Attachment created", "id": new_attribute.id}, 200

    @classmethod
    def remove_attachment(cls, report_item_id, attribute_id, user):
        report_item = cls.get(report_item_id)
        if not report_item:
            return {"error": f"No Report Item with id '{report_item_id}' found"}, 404
        attribute_to_delete = next(
            (attribute for attribute in report_item.attributes if attribute.id == attribute_id),
            None,
        )
        if attribute_to_delete is not None:
            report_item.attributes.remove(attribute_to_delete)

        report_item.last_updated = datetime.now()
        db.session.commit()

        return {"message": "Attachment deleted", "id": attribute_id}, 200

    def update_cpes(self):
        self.report_item_cpes = []
        if self.completed:
            for attribute in self.attributes:
                attribute_group = AttributeGroupItem.get(attribute.attribute_group_item_id)
                if not attribute_group:
                    continue
                if attribute_group.attribute.type == AttributeType.CPE:
                    self.report_item_cpes.append(ReportItemCpe(attribute.value))


class ReportItemCpe(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())

    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"))
    report_item = db.relationship("ReportItem")

    def __init__(self, value):
        self.id = None
        self.value = value
