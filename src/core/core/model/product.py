import binascii
import hashlib
import json
import mimetypes
from base64 import b64decode
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Mapped, contains_eager, deferred, joinedload, lazyload, load_only, relationship, selectinload
from sqlalchemy.sql import Select

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.product_type import ProductType
from core.model.report_item import ReportItem
from core.model.report_item_type import ReportItemType
from core.model.role_based_access import ItemType
from core.model.user import User
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class Product(BaseModel):
    __tablename__ = "product"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    title: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    created: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow)
    auto_publish: Mapped[bool] = db.Column(db.Boolean, default=False)

    product_type_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("product_type.id"))
    product_type: Mapped["ProductType"] = relationship("ProductType")

    report_items: Mapped[list["ReportItem"]] = relationship("ReportItem", secondary="product_report_item")
    default_publisher: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("publisher_preset.id"), nullable=True)
    last_rendered: Mapped[datetime | None] = db.Column(db.DateTime)
    last_published_url: Mapped[str | None] = db.Column(db.Text, nullable=True)
    render_result = deferred(db.Column(db.Text))

    def __init__(
        self,
        title: str,
        product_type_id: str,
        description: str = "",
        auto_publish: bool = False,
        report_items: list[str] | None = None,
        default_publisher: str | None = None,
        id: str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.title = title
        self.description = description
        self.product_type_id = product_type_id
        self.auto_publish = auto_publish
        self.default_publisher = default_publisher
        if report_items is not None:
            self.report_items = ReportItem.get_bulk(report_items)

    @classmethod
    def add(cls, data: dict[str, Any], user_id: str | None = None) -> "Product":
        product = cls.from_dict(data)
        db.session.add(product)
        db.session.commit()
        if data.get("report_items") is not None:
            queue_manager.queue_manager.generate_product(product.id, countdown=5, user_id=user_id)
        return product

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user: User) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.PRODUCT_TYPE)
        return RoleBasedAccessService.filter_query_with_acl(query, rbac)

    def get_supported_reports(self, user: User | None = None) -> list[ReportItem]:
        """Returns list of ReportItems that are have the correct 'report_item_type' of that is set by the 'product_type' of the current 'product'"""
        if not self.product_type or not self.product_type.report_types:
            return []

        allowed_type_ids = [rt.id for rt in self.product_type.report_types if rt]
        if not allowed_type_ids:
            return []

        query = ReportItem.get_filter_query_with_acl({}, user) if user else db.select(ReportItem)
        query = (
            query.where(ReportItem.report_item_type_id.in_(allowed_type_ids))
            .order_by(ReportItem.title, ReportItem.id)
            .options(
                lazyload(ReportItem.attributes),
                load_only(ReportItem.id, ReportItem.title, ReportItem.created, ReportItem.report_item_type_id),
                joinedload(ReportItem.report_item_type).load_only(ReportItemType.title),
            )
        )
        return list(db.session.execute(query).scalars().all())

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls).join(ProductType, cls.product_type_id == ProductType.id)

        if search := filter_args.get("search"):
            query = query.filter(
                db.or_(Product.title.ilike(f"%{search}%"), Product.description.ilike(f"%{search}%"), ProductType.title.ilike(f"%{search}%"))
            )

        if filter_range := filter_args.get("range"):
            filter_range = filter_range.upper()
            date_limit = BaseModel.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(Product.created >= date_limit)

        return query

    @classmethod
    def default_sort_column(cls) -> str:
        return "created_desc"

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict[str, Any], query: Select) -> Select:
        order = filter_args.get("order") or filter_args.get("sort") or cls.default_sort_column()
        order = {"DATE_DESC": "created_desc", "DATE_ASC": "created_asc"}.get(order, order)
        descending = order.endswith("_desc")
        if order in {"report_items_asc", "report_items_desc"}:
            column = db.select(func.count()).where(ProductReportItem.product_id == cls.id).correlate(cls).scalar_subquery()
        elif order in {"type_asc", "type_desc"}:
            column = cast(ProductType.type, String)
        else:
            return super()._add_sorting_to_query({"order": order}, query).order_by(cls.id.desc() if descending else cls.id.asc())
        return query.order_by(None).order_by(column.desc() if descending else column.asc(), cls.id.desc() if descending else cls.id.asc())

    @classmethod
    def get_all_for_api(cls, filter_args: dict[str, Any] | None, with_count: bool = False, user=None) -> tuple[dict[str, Any], int]:
        filter_args = filter_args or {}
        base_query = cls.get_filter_query_with_acl(filter_args, user) if user else cls.get_filter_query(filter_args)
        query = base_query if cls._should_fetch_all(filter_args) else cls._add_paging_to_query(filter_args, base_query)
        query = cls._add_sorting_to_query(filter_args, query).options(
            contains_eager(cls.product_type).load_only(ProductType.type),
            selectinload(cls.report_items).load_only(ReportItem.id).lazyload(ReportItem.attributes),
        )
        response: dict[str, Any] = {"items": cls.to_list(cls.get_filtered(query) or [])}
        if with_count:
            response["total_count"] = cls.get_filtered_count(base_query)
        return response, 200

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None = None, *, include_render: bool = True) -> tuple[dict[str, Any], int]:
        query = (
            cls.get_filter_query({})
            .where(cls.id == item_id)
            .options(
                contains_eager(cls.product_type).selectinload(ProductType.report_types).load_only(ReportItemType.id),
                selectinload(cls.report_items).load_only(ReportItem.id).lazyload(ReportItem.attributes),
            )
        )
        item = cls.get_first(query)
        if item is None:
            return {"error": "Product not found"}, 404
        if user and not item.product_type.allowed_with_acl(user, require_write_access=False):
            return {"error": "User is not allowed to read product"}, 403
        return item.to_detail_dict(user=user, include_render=include_render), 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict(exclude={"render_result"})
        data["type"] = self.product_type.type
        data["report_items"] = [report_item.id for report_item in self.report_items if report_item]
        return data

    @classmethod
    def get_choices_for_api(cls, user: User) -> tuple[dict[str, Any], int]:
        query = (
            cls.get_filter_query_with_acl({}, user)
            .with_only_columns(cls.id, cls.title, ProductType.title.label("product_type_title"))
            .order_by(cls.title, cls.id)
        )
        return {"items": [dict(row) for row in db.session.execute(query).mappings()]}, 200

    def to_detail_dict(self, user: User | None = None, *, include_render: bool = True) -> dict[str, Any]:
        data = self.to_dict()
        data["supported_reports"] = [r.to_supported_products_dict() for r in self.get_supported_reports(user)]
        if include_render:
            data["render_result"] = self.render_result
        data["mime_type"] = self.product_type.get_mimetype() if self.product_type else None
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.product_type.type,
            "type_id": self.product_type.id,
            "mime_type": self.product_type.get_mimetype(),
            "report_items": [report_item.to_product_dict() for report_item in self.report_items if report_item],
            "parameters": self.product_type.to_worker_dict()["parameters"],
        }
        data["render_revision"] = hashlib.sha256(json.dumps(data, separators=(",", ":"), default=str).encode()).hexdigest()
        return data

    @classmethod
    def test_if_valid_render_result(cls, render_result: str) -> bool:
        """
        Test if render_result is a valid base64 string
        :return: True if valid, False otherwise
        """
        try:
            b64decode(render_result)
            return True
        except (binascii.Error, TypeError, ValueError):
            logger.exception()
            return False

    def update_render(self, render_result: str) -> bool:
        if self.test_if_valid_render_result(render_result):
            self.last_rendered = self.utcnow()
            self.render_result = render_result
            db.session.commit()
            return True

        return False

    @classmethod
    def update_render_for_id(cls, product_id: str, render_result: str, render_revision: str):
        if not (product := cls.get(product_id)):
            return {"error": "Product not found"}, 404
        if render_revision != product.to_worker_dict()["render_revision"]:
            logger.warning("Discarded stale render result for Product %s", product_id)
            return {"error": "Stale product render"}, 409
        if product.update_render(render_result):
            logger.debug(f"Render result for Product {product_id} updated")
            return {"message": "Product updated"}, 200
        return {"error": "Product not updated"}, 500

    def get_file_name(self) -> str:
        product_title = self.title
        mime_type = self.product_type.get_mimetype()

        file_extension = mimetypes.guess_extension(mime_type, strict=False)
        if file_extension == ".stix":
            file_extension = ".json"
        return f"{product_title}_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}{file_extension}"

    @classmethod
    def get_render(cls, product_id: str):
        if (product := cls.get(product_id)) and product.render_result:
            return {"mime_type": product.product_type.get_mimetype(), "blob": product.render_result, "filename": product.get_file_name()}
        return None

    @classmethod
    def update(cls, product_id: str, data, user: User | None = None) -> tuple[dict, int]:
        product = Product.get(product_id)
        if product is None:
            return {"error": "Product not found"}, 404

        product_type = ProductType.get(data.get("product_type_id", product.product_type_id))
        if product_type is None:
            return {"error": "Product type not found"}, 404
        if user and not product_type.allowed_with_acl(user, require_write_access=False):
            return {"error": "User does not have access to this product type"}, 403

        report_item_ids = data.get("report_items")
        report_items = product.report_items if report_item_ids is None else ReportItem.get_bulk(report_item_ids)
        supported_report_type_ids = {report_type.id for report_type in product_type.report_types if report_type}
        selected_report_type_ids = {report_item.report_item_type_id for report_item in report_items if report_item.report_item_type_id}
        if unsupported_report_type_ids := selected_report_type_ids - supported_report_type_ids:
            logger.warning(
                "Rejected product type %s for product %s; unsupported report types: %s",
                product_type.id,
                product.id,
                sorted(map(str, unsupported_report_type_ids)),
            )
            return {"error": "Selected product type does not support the selected reports"}, 400

        product_type_changed = product_type.id != product.product_type_id
        mime_type_changed = product_type.get_mimetype() != product.product_type.get_mimetype()

        if title := data.get("title"):
            product.title = title

        product.description = data.get("description")
        product.product_type = product_type
        if product_type_changed:
            product.render_result = None
            product.last_rendered = None
        if mime_type_changed:
            product.last_published_url = None
        if report_item_ids is not None:
            product.report_items = report_items

        if "auto_publish" in data:
            product.auto_publish = data.get("auto_publish")
        if "default_publisher" in data:
            product.default_publisher = data.get("default_publisher") or None

        db.session.commit()
        queue_manager.queue_manager.generate_product(product.id, user_id=user.id if user else None)
        return {"message": "Product updated", "id": product.id, "product": product.to_detail_dict()}, 200

    @classmethod
    def get_for_worker(cls, item_id: str) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_worker_dict(), 200
        return {"error": f"{cls.__name__} not found"}, 404


class ProductReportItem(BaseModel):
    product_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    report_item_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)

    @classmethod
    def assigned(cls, report_id) -> bool:
        query = db.select(db.exists().where(cls.report_item_id == report_id))
        return db.session.execute(query).scalar_one()
