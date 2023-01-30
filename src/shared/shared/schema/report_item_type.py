from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.presentation import PresentationSchema
from shared.schema.attribute import AttributeSchema


class AttributeGroupItemSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    index = fields.Int()
    min_occurrence = fields.Int()
    max_occurrence = fields.Int()
    attribute = fields.Nested(AttributeSchema, allow_none=True, load_only=True)
    attribute_id = fields.Int(dump_only=True, allow_none=True)
    attribute_name = fields.Str(dump_only=True, allow_none=True)

    @post_load
    def make_attribute_group_item(self, data, **kwargs):
        return AttributeGroupItem(**data)


class AttributeGroupItem:
    def __init__(self, id, title, description, index, min_occurrence, max_occurrence, attribute):
        self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute = attribute


class AttributeGroupBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    section = fields.Int(allow_none=True)
    section_title = fields.Str(allow_none=True)
    index = fields.Int()

    @post_load
    def make_attribute_group(self, data, **kwargs):
        return AttributeGroup(**data)


class AttributeGroupSchema(AttributeGroupBaseSchema):
    attribute_group_items = fields.Nested(AttributeGroupItemSchema, many=True)


class AttributeGroup:
    def __init__(
        self,
        id,
        title,
        description,
        section,
        section_title,
        index,
        attribute_group_items,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items


class ReportItemTypeBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()


class ReportItemTypeSchema(ReportItemTypeBaseSchema):
    attribute_groups = fields.Nested(AttributeGroupSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return ReportItemType(**data)


class ReportItemTypePresentationSchema(ReportItemTypeSchema, PresentationSchema):
    pass


class ReportItemType:
    def __init__(self, id, title, description, attribute_groups):
        self.id = id
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups


class ReportItemTypeIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return ReportItemTypeId(**data)


class ReportItemTypeId:
    def __init__(self, id):
        self.id = id
