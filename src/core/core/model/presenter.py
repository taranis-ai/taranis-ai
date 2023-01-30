from marshmallow import post_load
import uuid
from sqlalchemy import or_, func

from core.managers.db_manager import db
from core.model.parameter import Parameter
from shared.schema.presenter import PresenterSchema


class NewPresenterSchema(PresenterSchema):
    @post_load
    def make(self, data, **kwargs):
        return Presenter(**data)


class Presenter(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship("Parameter", secondary="presenter_parameter")

    node_id = db.Column(db.String, db.ForeignKey("presenters_node.id"))
    node = db.relationship("PresentersNode", back_populates="presenters")

    product_types = db.relationship("ProductType", back_populates="presenter")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Presenter.name).like(search_string),
                    func.lower(Presenter.description).like(search_string),
                )
            )

        return query.order_by(db.asc(Presenter.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        presenters, count = cls.get(search)
        node_schema = PresenterSchema(many=True)
        items = node_schema.dump(presenters)

        return {"total_count": count, "items": items}

    @classmethod
    def create_all(cls, presenters_data):
        new_presenter_schema = NewPresenterSchema(many=True)
        return new_presenter_schema.load(presenters_data)

    @classmethod
    def to_dict(cls):
        presenter_schema = PresenterSchema()
        return presenter_schema.dump(Presenter(None, None, None, []))

    @classmethod
    def add(cls, data):
        if cls.find_by_type(data["type"]):
            return None
        schema = NewPresenterSchema()

        parameters = [Parameter.find_by_key(p) for p in data["parameters"] if p is not None]
        data["parameters"] = []
        presenter = schema.load(data)
        presenter.parameters = parameters

        db.session.add(presenter)
        db.session.commit()

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()


class PresenterParameter(db.Model):
    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"), primary_key=True)
    parameter_key = db.Column(db.String, db.ForeignKey("parameter.key"), primary_key=True)
