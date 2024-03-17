import os
from typing import Any
from sqlalchemy import or_, Column, String
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.base_model import BaseModel
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.model.parameter_value import ParameterValue
from core.model.report_item_type import ReportItemType
from core.model.worker import PRESENTER_TYPES, Worker
from core.managers.data_manager import get_presenter_template_path, get_presenter_templates, get_template_as_base64, write_base64_to_file
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class ProductType(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title: Column[String] = db.Column(db.String(64), unique=True, nullable=False)
    description: Column[String] = db.Column(db.String())
    type: Any = db.Column(db.Enum(PRESENTER_TYPES))

    parameters: Mapped[list["ParameterValue"]] = db.relationship(
        "ParameterValue", secondary="product_type_parameter_value", cascade="all, delete"
    )  # type: ignore
    report_types: Mapped[list["ReportItemType"]] = db.relationship(
        "ReportItemType", secondary="product_type_report_type", cascade="all, delete"
    )  # type: ignore

    def __init__(self, title, type, description=None, parameters=None, report_types=None, id=None):
        self.id = id
        self.title = title
        self.type = type
        if description:
            self.description = description
        self.parameters = Worker.parse_parameters(type, parameters)
        self.report_types = [ReportItemType.get(report_type) for report_type in report_types] if report_types else []

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(ProductType.title)).all()

    def allowed_with_acl(self, user, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(user=user, resource_id=str(self.id), resource_type=ItemType.PRODUCT_TYPE, require_write_access=require_write_access)

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(ProductType.id)

        if acl_check:
            rbac = RBACQuery(user=user, resource_type=ItemType.PRODUCT_TYPE)
            query = RoleBasedAccessService.filter_query_with_acl(query, rbac)

        if search:
            query = query.filter(
                or_(
                    ProductType.title.ilike(f"%{search}%"),
                    ProductType.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(ProductType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        product_types, count = cls.get_by_filter(search, user, acl_check)
        items = [product_type.to_dict() for product_type in product_types]
        return {"total_count": count, "items": items, "templates": get_presenter_templates()}

    @classmethod
    def update(cls, preset_id, data):
        product_type = cls.get(preset_id)
        if not product_type:
            logger.error(f"Could not find product type with id {preset_id}")
            return {"error": f"Could not find product type with id {preset_id}"}, 404
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
            product_type.report_types = [ReportItemType.get(report_type) for report_type in report_types]
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
    def get_by_type(cls, type) -> "ProductType":
        return cls.query.filter_by(type=type).first()

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


class ProductTypeParameterValue(BaseModel):
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)


class ProductTypeReportType(BaseModel):
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id", ondelete="CASCADE"), primary_key=True)
    report_item_type_id = db.Column(db.Integer, db.ForeignKey("report_item_type.id"), primary_key=True)
