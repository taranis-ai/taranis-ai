from typing import Any
from datetime import datetime
from sqlalchemy import func, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select

from core.managers.log_manager import logger
from core.model.report_item_type import ReportItemType
from core.model.attribute import Attribute
from core.model.news_item import NewsItemAggregate
from core.model.report_item_cpe import ReportItemCpe
from core.model.base_model import BaseModel


class ReportItem(BaseModel):
    """Report item model.

    Attributes:
        id: Primary key
        uuid: UUID of the report item
        title: Title
        title_prefix: Title prefix
        created: Creation timestamp
        last_updated: Last update timestamp
        completed: Whether the report item is completed
        user_id: User ID of the creator
        remote_user: Remote user name
        report_item_type_id: Foreign key to report item type
    """

    __tablename__ = "report_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(index=True, unique=True)
    title: Mapped[str]
    title_prefix: Mapped[str]
    created: Mapped[datetime]
    last_updated: Mapped[datetime]
    completed: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int | None]
    remote_user: Mapped[str | None]

    report_item_type_id: Mapped[int] = mapped_column(index=True)
    report_item_type: Mapped["ReportItemType"] = relationship("ReportItemType")

    attributes: Mapped[list["Attribute"]] = relationship(
        "Attribute",
        secondary="report_item_attribute",
        back_populates="report_items",
        cascade="all, delete",
    )

    news_item_aggregates: Mapped[list["NewsItemAggregate"]] = relationship(
        "NewsItemAggregate",
        secondary="news_item_aggregate_report_item",
        back_populates="report_items",
    )

    report_item_cpes: Mapped[list["ReportItemCpe"]] = relationship("ReportItemCpe", back_populates="report_item", cascade="all, delete-orphan")

    def __init__(
        self,
        id: int | None = None,
        uuid: str | None = None,
        title: str | None = None,
        title_prefix: str | None = None,
        created: datetime | None = None,
        last_updated: datetime | None = None,
        completed: bool = False,
        user_id: int | None = None,
        remote_user: str | None = None,
        report_item_type_id: int | None = None,
        report_item_type: ReportItemType | None = None,
        attributes: list | None = None,
        news_item_aggregates: list | None = None,
        report_item_cpes: list | None = None,
    ):
        self.id = id
        self.uuid = uuid or ""
        self.title = title or ""
        self.title_prefix = title_prefix or ""
        self.created = created or datetime.now()
        self.last_updated = last_updated or datetime.now()
        self.completed = completed
        self.user_id = user_id
        self.remote_user = remote_user
        self.report_item_type_id = report_item_type_id
        if report_item_type:
            self.report_item_type = report_item_type
        self.attributes = attributes or []
        self.news_item_aggregates = news_item_aggregates or []
        self.report_item_cpes = report_item_cpes or []

    @classmethod
    def get_filter_query_with_joins(cls, filter_args: dict) -> Select:
        """Get filter query with joins.

        Arguments:
            filter_args: filter arguments

        Returns:
            Query with joins
        """
        query = cls.get_filter_query(filter_args)

        return query.join(ReportItemType, cls.report_item_type)

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        """Get filter query.

        Arguments:
            filter_args: filter arguments

        Returns:
            Query
        """
        query = cls.get_base_query()

        if search := filter_args.get("search"):
            query = query.filter(
                or_(
                    func.lower(cls.title).like(func.lower(f"%{search}%")),
                    func.lower(cls.title_prefix).like(func.lower(f"%{search}%")),
                )
            )

        if completed := filter_args.get("completed"):
            query = query.filter(cls.completed == (completed == "true"))

        if range_filter := filter_args.get("range"):
            filter_range = range_filter.upper()
            if filter_range == "WEEK":
                query = query.filter(cls.created >= datetime.now() - datetime.timedelta(days=7))
            elif filter_range == "MONTH":
                query = query.filter(cls.created >= datetime.now() - datetime.timedelta(days=31))

        return query

    @classmethod
    def get_all_for_api(cls, filter_args: dict) -> tuple[list[dict[str, Any]], int]:
        query = cls.get_filter_query_with_joins(filter_args)
        return super().get_all_for_api_from_query(query, filter_args)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["report_item_type"] = self.report_item_type.to_dict()
        data["attributes"] = [attr.to_dict() for attr in self.attributes]
        data["news_item_aggregates"] = [agg.to_dict() for agg in self.news_item_aggregates]
        data["report_item_cpes"] = [cpe.to_dict() for cpe in self.report_item_cpes]
        return data

    @classmethod
    def get_detail_by_uuid(cls, report_item_uuid: str) -> dict[str, Any] | None:
        """Get report item detail by UUID.

        Arguments:
            report_item_uuid: Report item UUID

        Returns:
            Report item detail
        """
        if report_item := cls.get_by_uuid(report_item_uuid):
            return report_item.to_dict()
        return None

    @classmethod
    def delete_by_uuid(cls, report_item_uuid: str) -> dict[str, Any]:
        """Delete report item by UUID.

        Arguments:
            report_item_uuid: Report item UUID

        Returns:
            Success status
        """
        report_item = cls.get_by_uuid(report_item_uuid)
        if not report_item:
            logger.warning(f"Report item {report_item_uuid} not found")
            return {"error": "Report item not found"}

        report_item.delete()
        logger.info(f"Report item {report_item_uuid} deleted")
        return {"message": "Report item deleted", "id": report_item_uuid}

    @classmethod
    def update_by_uuid(cls, report_item_uuid: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update report item by UUID.

        Arguments:
            report_item_uuid: Report item UUID
            data: Update data

        Returns:
            Updated report item
        """
        report_item = cls.get_by_uuid(report_item_uuid)
        if not report_item:
            logger.warning(f"Report item {report_item_uuid} not found")
            return {"error": "Report item not found"}

        if "title" in data:
            report_item.title = data["title"]
        if "title_prefix" in data:
            report_item.title_prefix = data["title_prefix"]
        if "completed" in data:
            report_item.completed = data["completed"]

        report_item.last_updated = datetime.now()
        report_item.update()

        logger.info(f"Report item {report_item_uuid} updated")
        return report_item.to_dict()
