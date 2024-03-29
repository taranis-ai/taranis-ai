from datetime import datetime, timedelta

import uuid
from sqlalchemy import or_, text
from sqlalchemy.sql.expression import false

from typing import Any, Optional

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item import NewsItemAggregate
from core.model.report_item_type import ReportItemType
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.user import User
from core.log import logger
from core.model.attribute import AttributeType, AttributeEnum
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class ReportItemAttribute(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value: Any = db.Column(db.String())

    title = db.Column(db.String())
    description = db.Column(db.String())

    index = db.Column(db.Integer)
    multiple = db.Column(db.Boolean, default=False)
    attribute_type: AttributeType = db.Column(db.Enum(AttributeType))
    group_title = db.Column(db.String())
    render_data = db.Column(db.JSON)

    report_item_id = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=True)
    report_item = db.relationship("ReportItem")

    def __init__(
        self,
        value=None,
        title=None,
        description=None,
        index=None,
        multiple=None,
        attribute_type=None,
        group_title=None,
        render_data=None,
        id=None,
    ):
        self.id = id
        self.value = value or ""
        self.title = title
        self.description = description
        self.index = index
        self.multiple = multiple
        if attribute_type and attribute_type in AttributeType:
            self.attribute_type = attribute_type
        self.render_data = render_data
        self.group_title = group_title

    @classmethod
    def update_values_from_report(cls, attribute_data):
        # TODO: Add functionality to update multiple attributes at once, if muliple is True
        for attribute_dicts in attribute_data.values():
            for attribute_id, data in attribute_dicts.items():
                if report_item_attribute := cls.get(attribute_id):
                    report_item_attribute.value = data["value"]

        db.session.commit()

    @staticmethod
    def sort(report_item_attribute):
        return report_item_attribute.last_updated

    def to_product_dict(self):
        return {
            self.title: self.value,
        }

    def to_report_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "index": self.index,
            "multiple": self.multiple,
            "type": self.attribute_type.name,
            "group_title": self.group_title,
            "render_data": self.render_data,
            "value": self.value,
        }


class ReportItem(BaseModel):
    id: Any = db.Column(db.String(64), primary_key=True)

    title: Any = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)
    last_updated = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, default=False)

    user_id: Any = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user: Any = db.relationship("User")

    report_item_type_id: Any = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), nullable=True)
    report_item_type: Any = db.relationship("ReportItemType")

    news_item_aggregates: Any = db.relationship("NewsItemAggregate", secondary="report_item_news_item_aggregate")

    attributes: Any = db.relationship(
        "ReportItemAttribute",
        back_populates="report_item",
        cascade="all, delete-orphan",
    )

    report_item_cpes: Any = db.relationship("ReportItemCpe", cascade="all, delete-orphan", back_populates="report_item")

    def __init__(
        self,
        title,
        report_item_type_id,
        news_item_aggregates,
        attributes=None,
        completed=False,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.report_item_type_id = report_item_type_id
        self.attributes = attributes or []
        self.completed = completed
        self.report_item_cpes = []

        self.news_item_aggregates = [NewsItemAggregate.get(news_item_aggregate.id) for news_item_aggregate in news_item_aggregates]

    @classmethod
    def count_all(cls, is_completed):
        return cls.query.filter_by(completed=is_completed).count()

    @classmethod
    def get_json(cls, filter, user):
        reports = cls.get_by_filter(filter, user, True)
        items = [report.to_dict() for report in reports]
        return {"total_count": len(items), "items": items}

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

    def get_attribute_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        result = {}
        for attribute in self.attributes:
            group = attribute.group_title
            item_id = str(attribute.id)
            if group not in result:
                result[group] = {}
            result[group][item_id] = attribute.to_report_dict()
        return result

    def to_detail_dict(self):
        data = super().to_dict()
        data["attributes"] = self.get_attribute_dict()
        data["news_item_aggregates"] = [aggregate.to_dict() for aggregate in self.news_item_aggregates if aggregate]
        return data

    def to_product_dict(self):
        data = super().to_dict()
        data["attributes"] = {attribute.title: attribute.value for attribute in self.attributes} if self.attributes else {}
        data["news_item_aggregates"] = [aggregate.to_dict() for aggregate in self.news_item_aggregates if aggregate]
        return data

    @classmethod
    def from_dict(cls, data) -> "ReportItem":
        return cls(**data)

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["ReportItem"]:
        return [cls.from_dict(report_item) for report_item in data]

    @classmethod
    def add(cls, report_item_data, user):
        report_item = cls.from_dict(report_item_data)

        if not report_item.allowed_with_acl(user, True):
            return report_item, 403

        report_item.user_id = user.id
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
                attribute_enums = AttributeEnum.get_all_for_attribute(attribute_group_item.attribute.id)
                attribute_enum_data = [attribute_enum.to_small_dict() for attribute_enum in attribute_enums] if attribute_enums else None
                attr = {
                    "title": attribute_group_item.title,
                    "description": attribute_group_item.description,
                    "index": attribute_group_item.index,
                    "multiple": attribute_group_item.multiple,
                    "attribute_type": attribute_group_item.attribute.type,
                    "group_title": attribute_group.title,
                    "render_data": {},
                }
                if attribute_enum_data:
                    attr["render_data"]["attribute_enums"] = attribute_enum_data
                if default_value := attribute_group_item.attribute.default_value:
                    attr["render_data"]["default_value"] = default_value
                self.attributes.append(ReportItemAttribute(**attr))

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(
            user=user,
            resource_id=str(self.report_item_type_id),
            resource_type=ItemType.REPORT_ITEM_TYPE,
            require_write_access=require_write_access,
        )

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_by_filter(cls, filter: dict, user, acl_check: bool):
        query = cls.query
        query = query.join(ReportItemType, ReportItem.report_item_type_id == ReportItemType.id)
        if acl_check:
            rbac = RBACQuery(user=user, resource_type=ItemType.REPORT_ITEM_TYPE)
            query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
            query = RoleBasedAccessService.filter_report_query_with_tlp(query, user)

        if search := filter.get("search"):
            query = query.filter(or_(ReportItemType.title.ilike(f"%{search}%"), ReportItem.title.ilike(f"%{search}%")))

        completed = filter.get("completed", "").lower()
        if completed == "true":
            query = query.filter(ReportItem.completed)

        if completed == "false":
            query = query.filter(ReportItem.completed == false())

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

        return query.offset(offset).limit(limit).all()

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

        if not report_item.report_item_type.allowed_with_acl(user, True):
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
            ReportItemAttribute.update_values_from_report(attributes_data)

        if aggregate_ids := data.get("aggregate_ids"):
            report_item.news_item_aggregates = [NewsItemAggregate.get(aggregate_id) for aggregate_id in aggregate_ids]

        db.session.commit()

        logger.debug(f"Updated Report Item {report_item.id}")

        return {"message": "Successfully updated Report Item", "id": report_item.id}, 200

    @classmethod
    def delete(cls, id: int) -> tuple[dict[str, Any], int]:
        from core.model.product import Product

        report = cls.get(id)
        if not report:
            return {"error": "Report not found"}, 404

        if Product.query.filter(Product.report_items.any(id=report.id)).first():  # type: ignore
            return {"error": "Report is used in a product"}, 409

        db.session.delete(report)
        db.session.commit()
        return {"message": "Report successfully deleted"}, 200


class ReportItemCpe(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String())

    report_item_id = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"))
    report_item = db.relationship("ReportItem")

    def __init__(self, value):
        self.id = None
        self.value = value
