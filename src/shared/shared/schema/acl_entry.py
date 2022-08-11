from marshmallow import Schema, fields, EXCLUDE
from enum import Enum, auto
from marshmallow_enum import EnumField

from shared.schema.presentation import PresentationSchema
from shared.schema.role import RoleSchema
from shared.schema.user import UserSchemaBase


class ItemType(Enum):
    COLLECTOR = auto()
    OSINT_SOURCE = auto()
    OSINT_SOURCE_GROUP = auto()
    WORD_LIST = auto()
    REPORT_ITEM = auto()
    REPORT_ITEM_TYPE = auto()
    PRODUCT_TYPE = auto()
    DELEGATION = auto()


class ACLEntryStatusSchema(Schema):
    see = fields.Bool()
    access = fields.Bool()
    modify = fields.Bool()


class ACLEntrySchema(ACLEntryStatusSchema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Integer()
    name = fields.Str()
    description = fields.Str()

    item_type = EnumField(ItemType)
    item_id = fields.Str()

    everyone = fields.Bool()


class ACLEntryPresentationSchema(ACLEntrySchema, PresentationSchema):
    roles = fields.Nested(RoleSchema, many=True)
    users = fields.Nested(UserSchemaBase, many=True)
