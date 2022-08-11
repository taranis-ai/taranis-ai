from marshmallow import Schema, fields, post_load, EXCLUDE
from marshmallow_enum import EnumField
from enum import Enum, auto

from shared.schema.presentation import PresentationSchema


class AttributeType(Enum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()


class AttributeValidator(Enum):
    NONE = auto()
    EMAIL = auto()
    NUMBER = auto()
    RANGE = auto()
    REGEXP = auto()


class AttributeEnumSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Integer(load_default=-1)
    index = fields.Integer(load_default=-1)
    value = fields.Str()
    description = fields.Str()

    @post_load
    def make_attribute_enum(self, data, **kwargs):
        return AttributeEnum(**data)


class AttributeEnum:
    def __init__(self, index, value, description):
        self.index = index
        self.value = value
        self.description = description


class AttributeBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    type = EnumField(AttributeType)
    default_value = fields.Str(allow_none=True)
    validator = EnumField(AttributeValidator, allow_none=True)
    validator_parameter = fields.Str(allow_none=True)

    @post_load
    def make_attribute(self, data, **kwargs):
        return Attribute(**data)


class AttributeSchema(AttributeBaseSchema):
    attribute_enums = fields.Nested(AttributeEnumSchema, many=True)


class AttributePresentationSchema(AttributeSchema, PresentationSchema):
    attribute_enums_total_count = fields.Int()


class Attribute:
    def __init__(self, id, name, description, type, default_value, validator, validator_parameter):
        self.id = id
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter
