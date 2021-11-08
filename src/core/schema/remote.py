from marshmallow import Schema, fields

from schema.osint_source import OSINTSourcePresentationSchema
from schema.presentation import PresentationSchema
from schema.report_item_type import ReportItemTypePresentationSchema


class RemoteAccessSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    access_key = fields.Str()
    enabled = fields.Bool()
    osint_sources = fields.List(fields.Nested(OSINTSourcePresentationSchema))
    report_item_types = fields.List(fields.Nested(ReportItemTypePresentationSchema))


class RemoteAccessPresentationSchema(RemoteAccessSchema, PresentationSchema):
    last_synced = fields.DateTime('%d.%m.%Y - %H:%M:%s')


class RemoteNodeSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    remote_url = fields.Str()
    events_url = fields.Str()
    access_key = fields.Str()
    enabled = fields.Bool()
    sync_news_items = fields.Bool()
    sync_report_items = fields.Bool()
    osint_source_group_id = fields.Str(missing=None)


class RemoteNodePresentationSchema(RemoteNodeSchema, PresentationSchema):
    last_synced = fields.DateTime('%d.%m.%Y - %H:%M:%s')
    event_id = fields.Str()
