from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.presentation import PresentationSchema
from shared.schema.news_item import NewsItemAggregateSchema
from shared.schema.acl_entry import ACLEntryStatusSchema


class ReportItemAttributeBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(load_default=None)
    value = fields.Str()
    binary_mime_type = fields.Str(load_default=None)
    binary_description = fields.Str(load_default=None)
    attribute_group_item_title = fields.Str(load_default=None)
    attribute_group_item_id = fields.Integer(load_default=None)


class ReportItemAttributeSchema(ReportItemAttributeBaseSchema):
    created = fields.DateTime()
    last_updated = fields.DateTime()
    version = fields.Int()
    current = fields.Bool()

    @post_load
    def make(self, data, **kwargs):
        return ReportItemAttribute(**data)


class ReportItemAttribute:
    def __init__(
        self,
        id,
        value,
        binary_mime_type,
        binary_description,
        attribute_group_item_id,
        attribute_group_item_title,
        created,
        last_updated,
        version,
        current,
    ):
        self.id = id
        self.value = value
        self.created = created
        self.last_updated = last_updated
        self.version = version
        self.current = current
        self.binary_mime_type = binary_mime_type
        self.binary_description = binary_description
        self.attribute_group_item_id = attribute_group_item_id
        self.attribute_group_item_title = attribute_group_item_title


class ReportItemBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int(allow_none=True, load_default=None)
    uuid = fields.Str(allow_none=True)
    title = fields.Str()
    title_prefix = fields.Str()
    created = fields.DateTime()
    last_updated = fields.DateTime()
    completed = fields.Bool()
    report_item_type_id = fields.Int(load_default=None)


class RemoteReportItemSchema(ReportItemBaseSchema, PresentationSchema):
    remote_user = fields.Str(allow_none=True)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)


class ReportItemSchema(ReportItemBaseSchema):
    news_item_aggregates = fields.Nested(NewsItemAggregateSchema, many=True)
    remote_report_items = fields.Nested(RemoteReportItemSchema, many=True)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)
    remote_user = fields.Str(allow_none=True)

    @post_load
    def make(self, data, **kwargs):
        return ReportItem(**data)


class ReportItemAttributeRemoteSchema(Schema):
    attribute_group_item_title = fields.Str()
    value = fields.Str()


class ReportItemRemoteSchema(Schema):
    uuid = fields.Str(allow_none=True)
    title = fields.Str()
    title_prefix = fields.Str()
    completed = fields.Bool()
    attributes = fields.Nested(ReportItemAttributeRemoteSchema, many=True)


class ReportItemPresentationSchema(ReportItemBaseSchema, ACLEntryStatusSchema, PresentationSchema):
    remote_user = fields.Str(allow_none=True)


class ReportItem:
    def __init__(
        self,
        id,
        uuid,
        title,
        title_prefix,
        created,
        last_updated,
        completed,
        report_item_type_id,
        news_item_aggregates,
        remote_report_items,
        attributes,
        remote_user,
    ):
        self.id = id
        self.uuid = uuid
        self.title = title
        self.title_prefix = title_prefix
        self.created = created
        self.last_updated = last_updated
        self.completed = completed
        self.report_item_type_id = report_item_type_id
        self.news_item_aggregates = news_item_aggregates
        self.attributes = attributes
        self.remote_report_items = remote_report_items
        self.remote_user = remote_user


class ReportItemIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return ReportItemId(**data)


class ReportItemId:
    def __init__(self, id):
        self.id = id
