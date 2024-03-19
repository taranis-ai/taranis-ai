from datetime import datetime, timedelta
from typing import Any
from base64 import b64encode, b64decode
from sqlalchemy import or_
from sqlalchemy.orm import deferred, Mapped

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.role_based_access import ItemType
from core.model.report_item import ReportItem
from core.model.base_model import BaseModel
from core.model.product_type import ProductType
from core.service.role_based_access import RoleBasedAccessService, RBACQuery


class Product(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title: Any = db.Column(db.String(), nullable=False)
    description: Any = db.Column(db.String())

    created = db.Column(db.DateTime, default=datetime.now)

    product_type_id: Any = db.Column(db.Integer, db.ForeignKey("product_type.id"))
    product_type = db.relationship("ProductType")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")

    report_items: Mapped[list["ReportItem"]] = db.relationship(
        "ReportItem", secondary="product_report_item", cascade="all, delete"
    )  # type: ignore
    last_rendered = db.Column(db.DateTime)
    render_result = deferred(db.Column(db.Text))

    def __init__(self, title, product_type_id, description="", report_items=None, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.product_type_id = product_type_id
        self.report_items = [ReportItem.get(report_item) for report_item in report_items] if report_items else []

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def get_detail_json(cls, product_id):
        return product.to_dict() if (product := cls.get(product_id)) else None

    @classmethod
    def add_filter_to_query(cls, query, filter: dict):
        search = filter.get("search")
        if search and search != "":
            query = query.filter(
                or_(
                    Product.title.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                )
            )

        if "range" in filter and filter["range"].upper() != "ALL":
            filter_range = filter["range"].upper()
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(Product.created >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(Product.created))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(Product.created))

        return query

    @classmethod
    def get_by_filter(cls, filter, user):
        query = cls.query.distinct().group_by(Product.id)

        query = query.join(ProductType, ProductType.id == Product.product_type_id)
        rbac = RBACQuery(user, ItemType.PRODUCT_TYPE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)

        query = cls.add_filter_to_query(query, filter)

        offset = filter.get("offset", 0)
        limit = filter.get("limit", 20)
        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_json(cls, filter, user):
        results, count = cls.get_by_filter(filter, user)

        items = [product.to_dict() for product in results]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["report_items"] = [report_item.id for report_item in self.report_items if report_item]
        data.pop("render_result", None)
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.product_type.type,
            "type_id": self.product_type.id,
            "mime_type": self.product_type.get_mimetype(),
            "report_items": [report_item.to_product_dict() for report_item in self.report_items if report_item],
        }

    def update_render(self, render_result):
        try:
            self.last_rendered = datetime.now()
            self.render_result = b64encode(render_result).decode("ascii")
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    @classmethod
    def update_render_for_id(cls, product_id, render_result):
        product = cls.get(product_id)
        if not product:
            return {"error": f"Product {product_id} not found"}, 404
        if product.update_render(render_result):
            return {"message": f"Product {product_id} updated"}, 200
        return {"error": f"Product {product_id} not updated"}, 500

    @classmethod
    def get_render(cls, product_id):
        if product := cls.get(product_id):
            if product.render_result:
                mime_type = product.product_type.get_mimetype()
                if mime_type == "application/pdf":
                    blob = product.render_result
                else:
                    blob = b64decode(product.render_result).decode("utf-8")  # type: ignore
                return {"mime_type": product.product_type.get_mimetype(), "blob": blob}
        return None

    @classmethod
    def update(cls, product_id, data) -> tuple[dict, int]:
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
            product.report_items = [ReportItem.get(report_item) for report_item in report_items]

        db.session.commit()
        return {"message": f"Product {product_id} updated", "id": product_id}, 200


class ProductReportItem(BaseModel):
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
