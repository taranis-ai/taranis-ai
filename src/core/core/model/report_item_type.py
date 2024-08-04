import json
from typing import Any
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.attribute import Attribute
from core.service.role_based_access import RoleBasedAccessService, RBACQuery


class AttributeGroupItem(BaseModel):
    __tablename__ = "attribute_group_item"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    index: Mapped[int] = db.Column(db.Integer)
    required: Mapped[bool] = db.Column(db.Boolean, default=False)

    attribute_group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("attribute_group.id", ondelete="CASCADE"))
    attribute_group: Mapped["AttributeGroup"] = relationship("AttributeGroup")

    attribute_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute: Mapped["Attribute"] = relationship("Attribute")

    def __init__(self, title: str, description: str, index: int, attribute_id=None, attribute=None, required=False, id=None):
        if id:
            self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.required = required

        if attribute:
            if attr := Attribute.filter_by_name(attribute):
                attribute_id = attr.id

        if not attribute_id:
            raise ValueError("AttributeGroupItem requires either attribute_id or attribute")

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
    def from_dict(cls, data: dict[str, Any]) -> "AttributeGroupItem":
        data.pop("attribute_group_id", None)
        return cls(**data)

    def to_dict_with_group(self):
        data = self.to_dict()
        data["attribute_group"] = self.attribute_group.to_dict()
        return data


class AttributeGroup(BaseModel):
    __tablename__ = "attribute_group"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())

    index: Mapped[int] = db.Column(db.Integer)

    report_item_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("report_item_type.id", ondelete="CASCADE"))
    report_item_type: Mapped["ReportItemType"] = relationship("ReportItemType")

    attribute_group_items: Mapped[list["AttributeGroupItem"]] = relationship(
        "AttributeGroupItem",
        back_populates="attribute_group",
        cascade="all, delete-orphan",
    )

    def __init__(self, title, description, index, attribute_group_items=None, id=None):
        if id:
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
                    attribute_group_item.required = updated_attribute_group_item.required
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
    __tablename__ = "report_item_type"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())

    attribute_groups: Mapped[list["AttributeGroup"]] = relationship(
        "AttributeGroup",
        back_populates="report_item_type",
        cascade="all, delete-orphan",
    )

    def __init__(self, title: str, description: str = "", attribute_groups=None, id: int | None = None):
        self.title = title
        self.description = description
        self.attribute_groups = AttributeGroup.load_multiple(attribute_groups) if attribute_groups else []
        if id:
            self.id = id

    @classmethod
    def get_by_title(cls, title):
        return cls.get_first(db.select(cls).filter_by(title=title))

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.REPORT_ITEM_TYPE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(
            user=user, resource_id=str(self.id), resource_type=ItemType.REPORT_ITEM_TYPE, require_write_access=require_write_access
        )

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                db.or_(
                    cls.title.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(cls.title))

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
        query = db.select(cls)
        if source_ids:
            query = query.filter(cls.id.in_(source_ids))

        data = cls.get_filtered(query)
        if not data:
            return json.dumps({"error": "no sources found"}).encode("utf-8")

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
    def delete(cls, item_id: int) -> tuple[dict[str, Any], int]:
        from core.model.report_item import ReportItem
        from core.model.product_type import ProductType

        report_type = cls.get(item_id)
        if not report_type:
            return {"error": "Report type not found"}, 404

        if report := ReportItem.query.filter_by(report_item_type_id=item_id).first():
            return {"error": f"Report type is used in a report - {report.title}"}, 409

        if product_type := ProductType.query.filter(ProductType.report_types.any(id=item_id)).first():  # type: ignore
            return {"error": f"Report is used in a product type - {product_type.title}"}, 409

        db.session.delete(report_type)
        db.session.commit()
        return {"message": f"ReportItemType {item_id} deleted"}, 200
