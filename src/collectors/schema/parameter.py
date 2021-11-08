from enum import Enum, auto
from marshmallow import Schema, fields, post_load
from marshmallow_enum import EnumField


class ParameterType(Enum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()


class ParameterSchema(Schema):
    id = fields.Int()
    key = fields.Str()
    name = fields.Str()
    description = fields.Str()
    type = EnumField(ParameterType)

    @post_load
    def make_parameter(self, data, **kwargs):
        return Parameter(**data)


class Parameter:

    def __init__(self, id, key, name, description, type):
        self.id = id
        self.key = key
        self.name = name
        self.description = description
        self.type = type
