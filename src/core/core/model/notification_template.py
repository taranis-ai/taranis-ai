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

    organizations = db.relationship("Organization", secondary="notification_template_organization")

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

        if organization is not None:
            query = query.join(
                NotificationTemplateOrganization,
                NotificationTemplate.id == NotificationTemplateOrganization.notification_template_id,
            )

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(NotificationTemplate.name).like(search_string),
                    func.lower(NotificationTemplate.description).like(search_string),
                )
            )

        return query.order_by(db.asc(NotificationTemplate.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, user, search):
        templates, count = cls.get(search, user.organizations[0])
        template_schema = NotificationTemplatePresentationSchema(many=True)
        return {"total_count": count, "items": template_schema.dump(templates)}

    @classmethod
    def add(cls, user, data):
        new_template_schema = NewNotificationTemplateSchema()
        template = new_template_schema.load(data)
        template.organizations = user.organizations
        db.session.add(template)
        db.session.commit()

    @classmethod
    def delete(cls, user, template_id):
        template = cls.query.get(template_id)
        if any(org in user.organizations for org in template.organizations):
            db.session.delete(template)
            db.session.commit()

    @classmethod
    def update(cls, user, template_id, data):
        new_template_schema = NewNotificationTemplateSchema()
        for r in data["recipients"]:
            r.pop("id")
        updated_template = new_template_schema.load(data)
        template = cls.query.get(template_id)
        if any(org in user.organizations for org in template.organizations):
            template.name = updated_template.name
            template.description = updated_template.description
            template.message_title = updated_template.message_title
            template.message_body = updated_template.message_body
            template.recipients = updated_template.recipients
            db.session.commit()


class NotificationTemplateOrganization(db.Model):
    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)
