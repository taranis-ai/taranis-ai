import os
import base64
from typing import Any
from sqlalchemy import or_, and_
import sqlalchemy
from sqlalchemy.sql.expression import cast

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.product import Product
from core.model.base_model import BaseModel
from core.model.acl_entry import ACLEntry, ItemType
from core.model.parameter_value import ParameterValue
from core.model.worker import PRESENTER_TYPES, Worker
from core.managers.data_manager import get_presenter_template_path, get_presenter_templates


class ProductType(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title: Any = db.Column(db.String(64), unique=True, nullable=False)
    description: Any = db.Column(db.String(), nullable=False)
    type: Any = db.Column(db.Enum(PRESENTER_TYPES))

    parameters = db.relationship("ParameterValue", secondary="product_type_parameter_value", cascade="all, delete")

    def __init__(self, title, type, description="", parameters=None, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.type = type
        self.parameters = Worker.parse_parameters(type, parameters)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(ProductType.title)).all()

    @classmethod
    def allowed_with_acl(cls, product_id, user, see, access, modify):
        product = db.session.query(Product).filter_by(id=product_id).first()
        if not product:
            return False

        query = db.session.query(ProductType.id).distinct().group_by(ProductType.id).filter(ProductType.id == product.product_type_id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.PRODUCT_TYPE,
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(ProductType.id)

        if acl_check:
            query = query.outerjoin(
                ACLEntry,
                and_(
                    cast(ProductType.id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.PRODUCT_TYPE,
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

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
            return None
        if title := data.get("title"):
            product_type.title = title
        if description := data.get("description"):
            product_type.description = description
        if type := data.get("type"):
            product_type.type = type
            product_type.parameters = Worker.parse_parameters(type, data.get("parameters", product_type.parameters))
        elif parameters := data.get("parameters"):
            updated_product_type = ParameterValue.get_or_create_from_list(parameters)
            product_type.parameters = ParameterValue.get_update_values(product_type.parameters, updated_product_type)
        db.session.commit()
        return product_type.id

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
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

    def _file_to_base64(self, filepath: str) -> str:
        try:
            with open(filepath, "rb") as f:
                file_content = f.read()
            return base64.b64encode(file_content).decode("utf-8")
        except Exception as e:
            print(f"An error occurred: {e}")
            return ""

    def get_detail_json(self):
        data = self.to_dict()
        if template := self.get_template():
            data["template"] = self._file_to_base64(template)
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
