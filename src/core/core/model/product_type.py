import datetime
from marshmallow import post_load, fields
from sqlalchemy import func, or_, orm, and_
import sqlalchemy
from sqlalchemy.sql.expression import cast

from core.managers.db_manager import db
from core.model.product import Product
from core.model.parameter_value import ParameterValueImportSchema
from core.model.acl_entry import ACLEntry
from shared.schema.acl_entry import ItemType
from shared.schema.product_type import ProductTypePresentationSchema, ProductTypeSchema


class NewProductTypeSchema(ProductTypeSchema):
    parameter_values = fields.List(fields.Nested(ParameterValueImportSchema))

    @post_load
    def make(self, data, **kwargs):
        return ProductType(**data)


class ProductType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(), nullable=False)

    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"))
    presenter = db.relationship("Presenter")

    parameter_values = db.relationship("ParameterValue", secondary="product_type_parameter_value", cascade="all")

    def __init__(self, id, title, description, presenter_id, parameter_values):
        self.id = None
        self.title = title
        self.description = description
        self.presenter_id = presenter_id
        self.parameter_values = parameter_values
        self.tag = "mdi-file-document-outline"

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-file-document-outline"

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
    def get(cls, search, user, acl_check):
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

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(ProductType.title).like(search_string),
                    func.lower(ProductType.description).like(search_string),
                )
            )

        return query.order_by(db.asc(ProductType.title)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        product_types, count = cls.get(search, user, acl_check)
        product_type_schema = ProductTypePresentationSchema(many=True)
        return {"total_count": count, "items": product_type_schema.dump(product_types)}

    @classmethod
    def add_new(cls, data):
        new_product_type_schema = NewProductTypeSchema()
        product_type = new_product_type_schema.load(data)
        db.session.add(product_type)
        db.session.commit()

    @classmethod
    def delete(cls, id):
        product_type = cls.query.get(id)
        db.session.delete(product_type)
        db.session.commit()

    @classmethod
    def update(cls, preset_id, data):
        new_product_type_schema = NewProductTypeSchema()
        updated_product_type = new_product_type_schema.load(data)
        product_type = cls.query.get(preset_id)
        product_type.title = updated_product_type.title
        product_type.description = updated_product_type.description

        for value in product_type.parameter_values:
            for updated_value in updated_product_type.parameter_values:
                if value.parameter_key == updated_value.parameter_key:
                    value.value = updated_value.value

        db.session.commit()


class ProductTypeParameterValue(db.Model):
    product_type_id = db.Column(db.Integer, db.ForeignKey("product_type.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
