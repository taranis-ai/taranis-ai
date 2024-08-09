import os
from typing import Any
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.log import logger
from core.model.base_model import BaseModel
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.parameter_value import ParameterValue
from core.model.report_item_type import ReportItemType
from core.model.worker import PRESENTER_TYPES, Worker
from core.managers.data_manager import get_presenter_template_path, get_presenter_templates, get_template_as_base64, write_base64_to_file
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class ProductType(BaseModel):
    __tablename__ = "product_type"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[PRESENTER_TYPES] = db.Column(db.Enum(PRESENTER_TYPES))

    parameters: Mapped[list["ParameterValue"]] = relationship(
        "ParameterValue", secondary="product_type_parameter_value", cascade="all, delete"
    )
    report_types: Mapped[list["ReportItemType"]] = relationship("ReportItemType", secondary="product_type_report_type", cascade="all, delete")

    def __init__(self, title, type, description="", parameters=None, report_types=None, id=None):
        if id:
            self.id = id
        self.title = title
        self.type = type
        self.description = description
        self.parameters = Worker.parse_parameters(type, parameters)
        if report_types:
            self.report_types = ReportItemType.get_bulk(report_types)

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(user=user, resource_id=str(self.id), resource_type=ItemType.PRODUCT_TYPE, require_write_access=require_write_access)

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                db.or_(
                    cls.title.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                    cls.type.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(cls.title))

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.PRODUCT_TYPE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    @classmethod
    def get_all_for_api(cls, filter_args: dict | None, with_count: bool = False, user=None) -> tuple[dict[str, Any], int]:
        filter_args = filter_args or {}
        logger.debug(f"Filtering {cls.__name__} with {filter_args}")
        if user:
            query = cls.get_filter_query_with_acl(filter_args, user)
        else:
            query = cls.get_filter_query(filter_args)
        items = cls.get_filtered(query)
        if not items:
            return {"items": []}, 200
        if with_count:
            count = cls.get_filtered_count(query)
            return {"total_count": count, "items": cls.to_list(items), "templates": get_presenter_templates()}, 200
        return {"items": cls.to_list(items), "templates": get_presenter_templates()}, 200

    @classmethod
    def update(cls, product_type_id: int, data, user=None) -> tuple[dict, int]:
        product_type = cls.get(product_type_id)
        if not product_type:
            logger.error(f"Could not find product type with id {product_type_id}")
            return {"error": f"Could not find product type with id {product_type_id}"}, 404
        if user and not product_type.allowed_with_acl(user, require_write_access=True):
            logger.error(f"User {user} does not have write access to product type {product_type_id}")
            return {"error": f"User {user} does not have write access to product type {product_type_id}"}, 403

        if title := data.get("title"):
            product_type.title = title

        product_type.description = data.get("description")

        if type := data.get("type"):
            product_type.type = type
            product_type.parameters = Worker.parse_parameters(type, data.get("parameters", product_type.parameters))
        elif parameters := data.get("parameters"):
            updated_product_type = ParameterValue.get_or_create_from_list(parameters)
            product_type.parameters = ParameterValue.get_update_values(product_type.parameters, updated_product_type)
        report_types = data.get("report_types", None)
        if report_types is not None:
            product_type.report_types = ReportItemType.get_bulk(report_types)
        if template_data := data.get("template"):
            if template_path := product_type.get_template():
                write_base64_to_file(template_data, template_path)
        db.session.commit()
        return {"message": f"Updated product type {product_type.title}", "id": product_type.id}, 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["report_types"] = [report_type.id for report_type in self.report_types if report_type]
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    def _get_template_path(self) -> str:
        # get value of parameter where parameter.parameter == "TEMPLATE_PATH"
        template_path = next((parameter.value for parameter in self.parameters if parameter.parameter == "TEMPLATE_PATH"), None)
        if not template_path:
            logger.error(f"Could not find template path for product type {self.title}")
            return ""
        return str(template_path)

    def get_template(self) -> str:
        full_path = get_presenter_template_path(self._get_template_path())
        return full_path if os.path.isfile(full_path) else ""

    def get_detail_json(self):
        data = self.to_dict()
        if template := self.get_template():
            data["template"] = get_template_as_base64(template)
        return data

    @classmethod
    def get_for_api(cls, item_id) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.get_detail_json(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    @classmethod
    def get_by_type(cls, product_type: PRESENTER_TYPES) -> "ProductType|None":
        return cls.get_first(db.select(cls).filter_by(type=product_type))

    def get_mimetype(self) -> str:
        if self.type.startswith("image"):
            return "image/png"
        if self.type.startswith("pdf"):
            return "application/pdf"
        if self.type.startswith("html"):
            return "text/html"
        if self.type.startswith("text"):
            return "text/plain"
        if self.type.startswith("json"):
            return "application/json"
        return "application/octet-stream"

    @classmethod
    def delete(cls, product_id: int) -> tuple[dict[str, Any], int]:
        from core.model.product import Product

        product_type = cls.get(product_id)
        if not product_type:
            return {"error": "Product type not found"}, 404

        if product := Product.query.where(Product.product_type_id == product_id).first():
            return {"error": f"Product type is used in a product - {product.title}"}, 409

        db.session.delete(product_type)
        db.session.commit()
        return {"message": f"Product type {product_id} deleted"}, 200


class ProductTypeParameterValue(BaseModel):
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)


class ProductTypeReportType(BaseModel):
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id", ondelete="CASCADE"), primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), primary_key=True)
