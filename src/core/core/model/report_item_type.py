from typing import Any
from sqlalchemy import or_, and_
import sqlalchemy
from sqlalchemy.sql.expression import cast

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.acl_entry import ACLEntry, ItemType
from core.managers.log_manager import logger


class AttributeGroupItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    index = db.Column(db.Integer)
    min_occurrence = db.Column(db.Integer, default=1)
    max_occurrence = db.Column(db.Integer, default=1)

    attribute_group_id = db.Column(db.Integer, db.ForeignKey("attribute_group.id", ondelete="CASCADE"))
    attribute_group = db.relationship("AttributeGroup")

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute")

    def __init__(self, title, description, index, attribute_id, min_occurrence=1, max_occurrence=1, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_id = attribute_id

    @staticmethod
    def sort(attribute_group_item):
        return attribute_group_item.index

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["attribute"] = self.attribute.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportItemType":
        data.pop("attribute_group_id", None)
        data.pop("attribute", None)
        return cls(**data)

    def to_dict_with_group(self):
        data = self.to_dict()
        data["attribute_group"] = self.attribute_group.to_dict()
        return data


class AttributeGroup(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    section = db.Column(db.Integer, default=0)
    section_title = db.Column(db.String(), default="")
    index = db.Column(db.Integer)

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id", ondelete="CASCADE"))
    report_item_type = db.relationship("ReportItemType")

    attribute_group_items = db.relationship(
        "AttributeGroupItem",
        back_populates="attribute_group",
        cascade="all, delete-orphan",
    )

    def __init__(self, title, description, index, attribute_group_items, section=0, section_title="", id=None):
        self.id = id
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttributeGroup":
        attribute_group_items = [
            AttributeGroupItem.from_dict(attribute_group_item) for attribute_group_item in data.pop("attribute_group_items")
        ]
        data.pop("report_item_type_id", None)
        return cls(attribute_group_items=attribute_group_items, **data)

    def to_dict(self):
        data = super().to_dict()
        data["attribute_group_items"] = [attribute_group_item.to_dict() for attribute_group_item in self.attribute_group_items]
        return data

    @staticmethod
    def sort(attribute_group):
        return attribute_group.index

    def update(self, updated_attribute_group):
        self.title = updated_attribute_group.title
        self.description = updated_attribute_group.description
        self.section = updated_attribute_group.section
        self.section_title = updated_attribute_group.section_title
        self.index = updated_attribute_group.index

        for updated_attribute_group_item in updated_attribute_group.attribute_group_items:
            found = False
            for attribute_group_item in self.attribute_group_items:
                if updated_attribute_group_item.id == attribute_group_item.id:
                    attribute_group_item.title = updated_attribute_group_item.title
                    attribute_group_item.description = updated_attribute_group_item.description
                    attribute_group_item.index = updated_attribute_group_item.index
                    attribute_group_item.min_occurrence = updated_attribute_group_item.min_occurrence
                    attribute_group_item.max_occurrence = updated_attribute_group_item.max_occurrence
                    attribute_group_item.attribute_id = updated_attribute_group_item.attribute_id
                    found = True
                    break

            if found is False:
                updated_attribute_group_item.attribute_group = None
                self.attribute_group_items.append(updated_attribute_group_item)

        for attribute_group_item in self.attribute_group_items[:]:
            found = any(
                updated_attribute_group_item.id == attribute_group_item.id
                for updated_attribute_group_item in updated_attribute_group.attribute_group_items
            )
            if not found:
                self.attribute_group_items.remove(attribute_group_item)


class ReportItemType(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    attribute_groups = db.relationship(
        "AttributeGroup",
        back_populates="report_item_type",
        cascade="all, delete-orphan",
    )

    def __init__(self, title, description, attribute_groups, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups

    @classmethod
    def get_all(cls):
        return cls.query.order_by(ReportItemType.title).all()

    @classmethod
    def get_by_title(cls, title):
        return cls.query.filter_by(title=title).first()

    @classmethod
    def allowed_with_acl(cls, report_item_type_id, user, see, access, modify):
        query = db.session.query(ReportItemType.id).distinct().group_by(ReportItemType.id).filter(ReportItemType.id == report_item_type_id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE,
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(ReportItemType.id)

        if acl_check:
            query = query.outerjoin(
                ACLEntry,
                and_(
                    cast(ReportItemType.id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.REPORT_ITEM_TYPE,
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    ReportItemType.title.ilike(search_string),
                    ReportItemType.description.ilike(search_string),
                )
            )

        return query.order_by(db.asc(ReportItemType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        report_item_types, count = cls.get_by_filter(search, user, acl_check)
        items = [report_item_type.to_dict() for report_item_type in report_item_types]
        return {"total_count": count, "items": items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportItemType":
        logger.debug(data)
        attribute_groups = [AttributeGroup.from_dict(attribute_group) for attribute_group in data.pop("attribute_groups")]
        return cls(attribute_groups=attribute_groups, **data)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["attribute_groups"] = [attribute_group.to_dict() for attribute_group in self.attribute_groups]
        return data

    @classmethod
    def update(cls, report_type_id, data) -> "ReportItemType | None":
        report_type = cls.get(report_type_id)
        if not report_type:
            return None
        if title := data.get("title"):
            report_type.title = title
        if description := data.get("description"):
            report_type.description = description
        if attribute_groups := data.get("attribute_groups"):
            report_type.attribute_groups = [AttributeGroup.from_dict(attribute_group) for attribute_group in attribute_groups]
        for attribute_group in report_type.attribute_groups:
            attribute_group.report_item_type = report_type
        db.session.commit()
        return report_type
