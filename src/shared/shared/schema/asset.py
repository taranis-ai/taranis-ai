from marshmallow import Schema, fields, EXCLUDE

from shared.schema.presentation import PresentationSchema
from shared.schema.report_item import ReportItemBaseSchema, ReportItemAttributeSchema
from shared.schema.user import UserSchemaBase
from shared.schema.notification_template import NotificationTemplateSchema
from shared.schema.report_item_type import ReportItemTypeSchema


class AssetCpeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    value = fields.Str()


class AssetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    serial = fields.Str()
    description = fields.Str()
    asset_group_id = fields.Str()
    asset_cpes = fields.Nested(AssetCpeSchema, many=True)


class ReportItemVulnerabilitySchema(ReportItemBaseSchema, PresentationSchema):
    report_item_type = fields.Nested(ReportItemTypeSchema)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)


class AssetVulnerabilitySchema(Schema):
    report_item = fields.Nested(ReportItemVulnerabilitySchema)
    solved = fields.Bool()


class AssetPresentationSchema(AssetSchema, PresentationSchema):
    vulnerabilities_count = fields.Int()
    vulnerabilities = fields.Nested(AssetVulnerabilitySchema, many=True)


class AssetGroupSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class AssetGroupPresentationSchema(AssetGroupSchema, PresentationSchema):
    users = fields.Nested(UserSchemaBase, many=True)
    templates = fields.Nested(NotificationTemplateSchema, many=True)
