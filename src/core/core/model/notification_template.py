from sqlalchemy import orm, func, or_
from marshmallow import post_load, fields

from core.managers.db_manager import db
from shared.schema.notification_template import (
    NotificationTemplatePresentationSchema,
    NotificationTemplateSchema,
    EmailRecipientSchema,
)


class NewEmailRecipientSchema(EmailRecipientSchema):
    @post_load
    def make(self, data, **kwargs):
        return EmailRecipient(**data)


class EmailRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(), nullable=False)
    name = db.Column(db.String())

    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"))

    def __init__(self, email, name):
        self.id = None
        self.email = email
        self.name = name


class NewNotificationTemplateSchema(NotificationTemplateSchema):
    recipients = fields.Nested(NewEmailRecipientSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return NotificationTemplate(**data)


class NotificationTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    message_title = db.Column(db.String())
    message_body = db.Column(db.String())

    recipients = db.relationship("EmailRecipient", cascade="all, delete-orphan")

    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization = db.relationship("Organization")

    def __init__(self, id, name, description, message_title, message_body, recipients):
        self.id = None
        self.name = name
        self.description = description
        self.message_title = message_title
        self.message_body = message_body
        self.recipients = recipients
        self.tag = "mdi-email-outline"

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-email-outline"

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @classmethod
    def get(cls, search, organization):
        query = cls.query

        if organization:
            query = query.filter_by(organization_id=organization.id)

        if search:
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    NotificationTemplate.name.ilike(search_string),
                    NotificationTemplate.description.ilike(search_string),
                )
            )

        return query.order_by(db.asc(NotificationTemplate.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, user, search):
        templates, count = cls.get(search, user.organization)
        template_schema = NotificationTemplatePresentationSchema(many=True)
        return {"total_count": count, "items": template_schema.dump(templates)}

    @classmethod
    def add(cls, user, data):
        new_template_schema = NewNotificationTemplateSchema()
        template = new_template_schema.load(data)
        template.organization = user.organization
        db.session.add(template)
        db.session.commit()
