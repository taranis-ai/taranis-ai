from datetime import datetime, timedelta
from typing import Any
import uuid
from base64 import b64decode
from sqlalchemy.orm import deferred, Mapped, relationship
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.log import logger
from core.model.role_based_access import ItemType
from core.model.report_item import ReportItem
from core.model.base_model import BaseModel
from core.model.user import User
from core.model.product_type import ProductType
from core.service.role_based_access import RoleBasedAccessService, RBACQuery
from core.managers import queue_manager


class Product(BaseModel):
    __tablename__ = "product"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    title: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    created: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)
    auto_publish: Mapped[bool] = db.Column(db.Boolean, default=False)  # to be implemented

    product_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("product_type.id"))
    product_type: Mapped["ProductType"] = relationship("ProductType")

    report_items: Mapped[list["ReportItem"]] = relationship("ReportItem", secondary="product_report_item")
    last_rendered: Mapped[datetime] = db.Column(db.DateTime)
    render_result = deferred(db.Column(db.Text))

    def __init__(self, title: str, product_type_id: int, description: str = "", report_items: list[str] | None = None, id: str | None = None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.product_type_id = product_type_id
        if report_items is not None:
            self.report_items = ReportItem.get_bulk(report_items)
            queue_manager.queue_manager.generate_product(self.id, countdown=5)

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user: User) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.PRODUCT_TYPE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(
                db.or_(Product.title.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%"), ProductType.title.ilike(f"%{search}%"))
            )

        if filter_range := filter_args.get("range"):
            filter_range = filter_range.upper()
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(Product.created >= date_limit)

        if sort := filter_args.get("sort"):
            if sort == "DATE_DESC":
                query = query.order_by(db.desc(Product.created))

            elif sort == "DATE_ASC":
                query = query.order_by(db.asc(Product.created))

        return query

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["report_items"] = [report_item.id for report_item in self.report_items if report_item]
        data.pop("render_result", None)
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.product_type.type,
            "type_id": self.product_type.id,
            "mime_type": self.product_type.get_mimetype(),
            "report_items": [report_item.to_product_dict() for report_item in self.report_items if report_item],
        }

    @classmethod
    def test_if_valid_render_result(cls, render_result: str) -> bool:
        """
        Test if render_result is a valid base64 string
        :return: True if valid, False otherwise
        """
        try:
            b64decode(render_result)
            return True
        except Exception:
            logger.exception()
            return False

    def update_render(self, render_result: str) -> bool:
        if self.test_if_valid_render_result(render_result):
            self.last_rendered = datetime.now()
            self.render_result = render_result
            db.session.commit()
            return True

        return False

    @classmethod
    def update_render_for_id(cls, product_id: str, render_result: str):
        if not (product := cls.get(product_id)):
            return {"error": f"Product {product_id} not found"}, 404
        if product.update_render(render_result):
            logger.debug(f"Render result for Product {product_id} updated")
            return {"message": f"Product {product_id} updated"}, 200
        return {"error": f"Product {product_id} not updated"}, 500

    @classmethod
    def get_render(cls, product_id: str):
        if product := cls.get(product_id):
            if product.render_result:
                mime_type = product.product_type.get_mimetype()
                if mime_type == "application/pdf":
                    blob = product.render_result
                else:
                    blob = b64decode(product.render_result).decode("utf-8")
                return {"mime_type": mime_type, "blob": blob}
        return None

    @classmethod
    def update(cls, product_id: str, data) -> tuple[dict, int]:
        product = Product.get(product_id)
        if product is None:
            return {"error": f"Product {product_id} not found"}, 404

        if title := data.get("title"):
            product.title = title

        product.description = data.get("description")

        if data.get("product_type_id") != product.product_type_id:
            logger.warning("Product type change not supported")

        report_items = data.get("report_items")
        if report_items is not None:
            product.report_items = ReportItem.get_bulk(report_items)
            queue_manager.queue_manager.generate_product(product.id)

        db.session.commit()
        return {"message": f"Product {product_id} updated", "id": product_id}, 200

    @classmethod
    def get_for_worker(cls, item_id: str) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_worker_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404


class ProductReportItem(BaseModel):
    product_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    report_item_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)

    @classmethod
    def assigned(cls, report_id) -> bool:
        query = db.select(db.exists().where(cls.report_item_id == report_id))
        return db.session.execute(query).scalar_one()
