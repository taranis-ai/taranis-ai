from marshmallow import post_load

from core.managers.db_manager import db
from shared.schema.parameter import ParameterType, ParameterSchema


class NewParameterSchema(ParameterSchema):
    @post_load
    def make_parameter(self, data, **kwargs):
        return Parameter(**data)


class Parameter(db.Model):
    key = db.Column(db.String(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(ParameterType))

    def __init__(self, key, name, description, type):
        self.key = key
        self.name = name
        self.description = description
        self.type = type

    @classmethod
    def add(cls, data):
        if cls.get_by_key(data["key"]):
            return None
        schema = NewParameterSchema()
        param = schema.load(data)
        db.session.add(param)
        db.session.commit()

    @classmethod
    def find_by_key(cls, key):
        return cls.query.get(key)

    @classmethod
    def filter_by_key(cls, key):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def get_by_key(cls, key):
        param = cls.query.get(key)
        return ParameterSchema().dump(param) if param else None

    @classmethod
    def get_all_json(cls):
        param, count = cls.query.all(), cls.query.count()
        schema = ParameterSchema(many=True)
        items = schema.dump(param)

        return {"total_count": count, "items": items}
