from typing import Any
from sqlalchemy import or_
import json

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.attribute import Attribute
from core.service.role_based_access import RoleBasedAccessService, RBACQuery


class AttributeGroupItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    index = db.Column(db.Integer)
    multiple = db.Column(db.Boolean, default=False)

    attribute_group_id = db.Column(db.Integer, db.ForeignKey("attribute_group.id", ondelete="CASCADE"))
    attribute_group = db.relationship("AttributeGroup")

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute")

    def __init__(self, title, description, index, attribute_id=None, attribute=None, multiple=False, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.multiple = multiple

        if attribute:
            if attr := Attribute.filter_by_name(attribute):
                attribute_id = attr.id

        if not attribute_id:
            raise Exception("AttributeGroupItem requires either attribute_id or attribute")

        self.attribute_id = attribute_id

    @staticmethod
    def sort(attribute_group_item):
        return attribute_group_item.index

    def to_dict(self):
        data = super().to_dict()
        data["attribute"] = self.attribute.to_dict()
        return data

    def to_export_dict(self):
        data = super().to_dict()
        data.pop("id", None)
        data.pop("attribute_group_id", None)
        data.pop("attribute_id", None)
        data["attribute"] = self.attribute.name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportItemType":
        data.pop("attribute_group_id", None)
        return cls(**data)

    def to_dict_with_group(self):
        data = self.to_dict()
        data["attribute_group"] = self.attribute_group.to_dict()
        return data


class AttributeGroup(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    index = db.Column(db.Integer)

    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id", ondelete="CASCADE"))
    report_item_type = db.relationship("ReportItemType")

    attribute_group_items: Any = db.relationship(
        "AttributeGroupItem",
        back_populates="attribute_group",
        cascade="all, delete-orphan",
    )

    def __init__(self, title, description, index, attribute_group_items=None, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.attribute_group_items = AttributeGroupItem.load_multiple(attribute_group_items) if attribute_group_items else []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttributeGroup":
        data.pop("report_item_type_id", None)
        return cls(**data)

    def to_dict(self):
        data = super().to_dict()
        data["attribute_group_items"] = [attribute_group_item.to_dict() for attribute_group_item in self.attribute_group_items]
        return data

    def to_export_dict(self):
        data = super().to_dict()
        data.pop("id", None)
        data.pop("report_item_type_id", None)
        data["attribute_group_items"] = [attribute_group_item.to_export_dict() for attribute_group_item in self.attribute_group_items]
        return data

    @staticmethod
    def sort(attribute_group):
        return attribute_group.index

    def update(self, updated_attribute_group):
        self.title = updated_attribute_group.title
        self.description = updated_attribute_group.description
        self.index = updated_attribute_group.index

        for updated_attribute_group_item in updated_attribute_group.attribute_group_items:
            found = False
            for attribute_group_item in self.attribute_group_items:
                if updated_attribute_group_item.id == attribute_group_item.id:
                    attribute_group_item.title = updated_attribute_group_item.title
                    attribute_group_item.description = updated_attribute_group_item.description
                    attribute_group_item.index = updated_attribute_group_item.index
                    attribute_group_item.multiple = updated_attribute_group_item.multiple
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
    title: Any = db.Column(db.String())
    description: Any = db.Column(db.String())

    attribute_groups: Any = db.relationship(
        "AttributeGroup",
        back_populates="report_item_type",
        cascade="all, delete-orphan",
    )

    def __init__(self, title, description=None, attribute_groups=None, id=None):
        self.title = title
        self.description = description
        self.attribute_groups = AttributeGroup.load_multiple(attribute_groups) if attribute_groups else []
        if id:
            self.id = id

    @classmethod
    def get_all(cls):
        return cls.query.order_by(ReportItemType.title).all()

    @classmethod
    def get_by_title(cls, title):
        return cls.query.filter_by(title=title).first()

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(
            user=user, resource_id=str(self.id), resource_type=ItemType.REPORT_ITEM_TYPE, require_write_access=require_write_access
        )

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(ReportItemType.id)

        if acl_check:
            rbac = RBACQuery(user=user, resource_type=ItemType.REPORT_ITEM_TYPE)
            query = RoleBasedAccessService.filter_query_with_acl(query, rbac)

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

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["attribute_groups"] = [attribute_group.to_dict() for attribute_group in self.attribute_groups]
        return data

    def to_export_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("id", None)
        data["attribute_groups"] = [attribute_group.to_export_dict() for attribute_group in self.attribute_groups]
        return data

    @classmethod
    def update(cls, report_type_id, data) -> "ReportItemType | None":
        report_type = cls.get(report_type_id)
        if not report_type:
            return None
        if title := data.get("title"):
            report_type.title = title

        report_type.description = data.get("description")

        if attribute_groups := data.get("attribute_groups"):
            report_type.attribute_groups = AttributeGroup.load_multiple(attribute_groups)
        for attribute_group in report_type.attribute_groups:
            attribute_group.report_item_type = report_type
        db.session.commit()
        return report_type

    @classmethod
    def export(cls, source_ids=None):
        if source_ids:
            data = cls.query.filter(cls.id.in_(source_ids)).all()  # type: ignore
        else:
            data = cls.get_all()
        export_data = {"version": 1, "data": [report_type.to_export_dict() for report_type in data]}
        return json.dumps(export_data).encode("utf-8")

    @classmethod
    def load_json_content(cls, content) -> list:
        if content.get("version") != 1:
            raise ValueError("Invalid JSON file")
        if not content.get("data"):
            raise ValueError("No data found")
        return content["data"]

    @classmethod
    def import_report_type(cls, file) -> list | None:
        file_data = file.read().decode("utf8")
        file_content = json.loads(file_data)
        data = cls.load_json_content(content=file_content)

        return cls.add_multiple(data)

    @classmethod
    def delete(cls, id: int) -> tuple[dict[str, Any], int]:
        from core.model.report_item import ReportItem
        from core.model.product_type import ProductType

        report_type = cls.get(id)
        if not report_type:
            return {"error": "Report type not found"}, 404

        if ReportItem.query.filter_by(report_item_type_id=id).first():
            return {"error": "Report type is used in a report"}, 409

        if ProductType.query.filter(ProductType.report_types.any(id=id)).first():  # type: ignore
            return {"error": "Report is used in a product type"}, 409

        db.session.delete(report_type)
        db.session.commit()
        return {"message": f"ReportItemType {id} deleted"}, 200
