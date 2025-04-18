from datetime import datetime, timedelta

import uuid
from sqlalchemy import or_
from sqlalchemy.sql.expression import false
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship

from typing import Any, Optional

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.story import Story
from core.model.report_item_type import ReportItemType
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.user import User
from core.log import logger
from core.model.attribute import AttributeType, AttributeEnum
from core.service.role_based_access import RBACQuery, RoleBasedAccessService
from core.service.news_item_tag import NewsItemTagService


class ReportItem(BaseModel):
    __tablename__ = "report_item"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)

    title: Mapped[str] = db.Column(db.String())

    created: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)
    last_updated: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)
    completed: Mapped[bool] = db.Column(db.Boolean, default=False)

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    user: Mapped["User"] = relationship("User")

    report_item_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), nullable=True)
    report_item_type: Mapped["ReportItemType"] = relationship("ReportItemType")

    stories: Mapped[list["Story"]] = relationship(
        "Story", secondary="report_item_story", cascade="save-update, merge, delete", passive_deletes=True, single_parent=False
    )

    attributes: Mapped[list["ReportItemAttribute"]] = relationship(
        "ReportItemAttribute",
        back_populates="report_item",
        cascade="all, delete-orphan",
    )

    report_item_cpes: Mapped[list["ReportItemCpe"]] = relationship(
        "ReportItemCpe", cascade="all, delete-orphan", back_populates="report_item"
    )

    def __init__(
        self,
        title,
        report_item_type_id,
        stories=None,
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
        if stories is not None:
            self.stories = Story.get_bulk(stories)

    @classmethod
    def count_all(cls, is_completed):
        return cls.get_filtered_count(db.select(cls).filter_by(completed=is_completed))

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None = None) -> tuple[dict[str, Any], int]:
        # sourcery skip: assign-if-exp, reintroduce-else, swap-if-else-branches, use-named-expression
        item = cls.get(item_id)
        if not item:
            return {"error": f"{cls.__name__} {item_id} not found"}, 404
        if user and not item.allowed_with_acl(user, False):
            return {"error": f"User {user.id} is not allowed to read Report {item.id}"}, 403

        return item.to_detail_dict(), 200

    @classmethod
    def get_story_ids(cls, item_id):
        if report_item := cls.get(item_id):
            return [story.id for story in report_item.stories], 200
        return {"error": "Report Item not found"}, 404

    @classmethod
    def get_detail_json(cls, id):
        report_item = cls.get(id)
        return report_item.to_detail_dict() if report_item else None

    def to_dict(self):
        data = super().to_dict()
        data["stories"] = [story.id for story in self.stories]
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
        data["stories"] = [story.to_dict() for story in self.stories if story]
        return data

    def to_product_dict(self):
        data = super().to_dict()
        data["attributes"] = {attribute.title: attribute.value for attribute in self.attributes} if self.attributes else {}
        data["stories"] = [story.to_dict() for story in self.stories if story]
        return data

    def clone_report(self):
        attributes = [a.clone_attribute() for a in self.attributes]

        report = ReportItem(
            title=f"{self.title} ({datetime.now().isoformat()})",
            report_item_type_id=self.report_item_type_id,
            attributes=attributes,
            completed=self.completed,
            stories=[],
        )
        db.session.add(report)
        db.session.commit()
        return report

    @classmethod
    def clone(cls, report_id: str, user: User) -> tuple[dict[str, Any], int]:
        report = cls.get(report_id)
        if not report:
            return {"error": "Report not found"}, 404

        if not report.allowed_with_acl(user, True):
            return {"error": "Permission Denied"}, 403

        new_report = report.clone_report()
        return {"message": f"Successfully cloned Report {report_id} to new Report {new_report.id}", "id": new_report.id}, 200

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["ReportItem"]:
        return [cls.from_dict(report_item) for report_item in data]

    @classmethod
    def add(cls, report_item_data, user):
        report_item = cls.from_dict(report_item_data)

        if not report_item.allowed_with_acl(user, True):
            return report_item, 403

        if user:
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
                    "required": attribute_group_item.required,
                    "attribute_type": attribute_group_item.attribute.type,
                    "group_title": attribute_group.title,
                    "render_data": {},
                }
                if attribute_enum_data:
                    attr["render_data"]["attribute_enums"] = attribute_enum_data
                if default_value := attribute_group_item.attribute.default_value:
                    attr["render_data"]["default_value"] = default_value
                if attribute_group_item.attribute.type == AttributeType.TLP:
                    attr["value"] = "clear"
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
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)
        query = query.join(ReportItemType, ReportItem.report_item_type_id == ReportItemType.id)

        if search := filter_args.get("search"):
            query = query.where(or_(ReportItemType.title.ilike(f"%{search}%"), ReportItem.title.ilike(f"%{search}%")))

        if filter_range := filter_args.get("range"):
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range.upper() == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())
                query = query.filter(ReportItem.created >= date_limit)

            if filter_range.upper() == "MONTH":
                date_limit = date_limit.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(ReportItem.created >= date_limit)

        completed = filter_args.get("completed", "").lower()
        if completed == "true":
            query = query.filter(ReportItem.completed)

        if completed == "false":
            query = query.filter(ReportItem.completed == false())

        if sort := filter_args.get("sort"):
            if sort == "DATE_DESC":
                query = query.order_by(db.desc(ReportItem.created))

            elif sort == "DATE_ASC":
                query = query.order_by(db.asc(ReportItem.created))

        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)

        return query.offset(offset).limit(limit)

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user: User) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.REPORT_ITEM_TYPE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        query = RoleBasedAccessService.filter_report_query_with_tlp(query, user)
        return query

    @classmethod
    def get_by_cpe(cls, cpes):
        query = db.select(cls).distinct(cls.id).join(ReportItemCpe, ReportItem.id == ReportItemCpe.report_item_id)
        query = query.filter(ReportItemCpe.value.in_(cpes))
        return cls.get_filtered(query)

    @classmethod
    def get_report_item_and_check_permission(cls, report_id: str, user: User) -> tuple[Optional["ReportItem"], dict, int]:
        if not (report_item := cls.get(report_id)):
            return None, {"error": "Report Item not Found"}, 404

        if not report_item.allowed_with_acl(user, True):
            return None, {"error": f"User {user.id} is not allowed to update Report {report_item.id}"}, 403

        return report_item, {}, 200

    @classmethod
    def add_stories(cls, report_id: str, story_ids: list[str], user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(report_id, user)
        if err or not report_item:
            return err, status

        stories = Story.get_bulk(story_ids)
        report_item.stories.extend(stories)
        db.session.commit()

        for story in stories:
            NewsItemTagService.add_report_tag(story, report_item)

        return {"message": f"Successfully added {story_ids} to {report_item.id}"}, 200

    @classmethod
    def remove_stories(cls, report_id: str, story_ids: list[int], user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(report_id, user)
        if err or not report_item:
            return err, status

        stories_to_remove = [story for story in (Story.get(item_id) for item_id in story_ids) if story is not None]
        for story in stories_to_remove:
            NewsItemTagService.remove_report_tag(story, report_item.id)

        report_item.stories = [story for story in report_item.stories if story not in stories_to_remove]
        db.session.commit()

        return {"message": f"Successfully removed {story_ids} from {report_item.id}"}, 200

    @classmethod
    def set_stories(cls, report_id: str, story_ids: list, user: User) -> tuple[dict, int]:
        return cls.update_report_item(report_id, {"story_ids": story_ids}, user)

    def update_stories(self, story_ids: list[str]):
        new_stories = Story.get_bulk(story_ids)
        new_story_ids_set = set(story_ids)

        existing_story_ids_set = {story.id for story in self.stories}

        # Identify stories to add and remove
        stories_to_add = [story for story in new_stories if story.id not in existing_story_ids_set]
        stories_to_remove = [story for story in self.stories if story.id not in new_story_ids_set]

        # Add new stories and their tags
        for story in stories_to_add:
            NewsItemTagService.add_report_tag(story, self)
            self.stories.append(story)

        # Remove old stories and their tags
        for story in stories_to_remove:
            NewsItemTagService.remove_report_tag(story, self.id)
            self.stories.remove(story)

    def retag_stories(self):
        for story in self.stories:
            NewsItemTagService.remove_report_tag(story, self.id)
            NewsItemTagService.add_report_tag(story, self)

    @classmethod
    def update_report_item(cls, report_id: str, data: dict, user: User) -> tuple[dict, int]:
        report_item, err, status = cls.get_report_item_and_check_permission(report_id, user)
        retag_stories = False
        if err or not report_item:
            return err, status

        if title := data.get("title"):
            retag_stories = True
            report_item.title = title

        completed = data.get("completed")
        if completed is not None:
            report_item.completed = completed

        if attributes_data := data.pop("attributes", None):
            report_item.update_attributes(attributes_data)

        story_ids = data.get("story_ids")
        if story_ids is not None:
            report_item.update_stories(story_ids)

        db.session.commit()

        if retag_stories:
            report_item.retag_stories()

        logger.debug(f"Updated Report Item {report_item.id}")

        return {"message": "Successfully updated Report Item", "id": report_item.id}, 200

    def update_attributes(self, attributes_data: dict, commit=False):
        for attribute in self.attributes:
            update_value = attributes_data.get(str(attribute.id), {}).get("value", attribute.value)
            attribute.value = update_value

        if commit:
            db.session.commit()

    @classmethod
    def delete(cls, report_id: str) -> tuple[dict[str, Any], int]:
        from core.model.product import ProductReportItem

        report = cls.get(report_id)
        if not report:
            return {"error": "Report not found"}, 404

        if ProductReportItem.assigned(report_id):
            return {"error": "Report is used in a product"}, 409

        db.session.delete(report)
        db.session.commit()
        return {"message": "Report successfully deleted"}, 200


class ReportItemAttribute(BaseModel):
    __tablename__ = "report_item_attribute"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    value: Mapped[str] = db.Column(db.String())

    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())

    index: Mapped[int] = db.Column(db.Integer)
    required: Mapped[bool] = db.Column(db.Boolean, default=False)
    attribute_type: Mapped[AttributeType] = db.Column(db.Enum(AttributeType))
    group_title: Mapped[str] = db.Column(db.String())
    render_data = db.Column(db.JSON)

    report_item_id = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), nullable=True)
    report_item = relationship("ReportItem")

    def __init__(
        self,
        value=None,
        title=None,
        description=None,
        index=None,
        required=None,
        attribute_type=None,
        group_title=None,
        render_data=None,
        id=None,
    ):
        if id:
            self.id = id
        self.value = value or ""
        self.title = title or ""
        self.description = description or ""
        self.index = index or 0
        self.required = required or False
        if attribute_type and attribute_type in AttributeType:
            self.attribute_type = attribute_type
        self.render_data = render_data
        self.group_title = group_title or ""

    @classmethod
    def find_attribute_by_title(cls, report_item_id, title: str) -> "ReportItemAttribute | None":
        query = db.select(cls).filter_by(report_item_id=report_item_id, title=title)
        return cls.get_first(query)

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
            "required": self.required,
            "type": self.attribute_type.name,
            "group_title": self.group_title,
            "render_data": self.render_data,
            "value": self.value,
        }

    def clone_attribute(self):
        value = "" if self.attribute_type in [AttributeType.STORY] else self.value

        return ReportItemAttribute(
            value=value,
            title=self.title,
            description=self.description,
            index=self.index,
            required=self.required,
            attribute_type=self.attribute_type,
            group_title=self.group_title,
            render_data=self.render_data,
        )


class ReportItemCpe(BaseModel):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    value: Mapped[str] = db.Column(db.String())

    report_item_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"))
    report_item: Mapped["ReportItem"] = relationship("ReportItem")

    def __init__(self, value):
        self.value = value
