from sqlalchemy import or_

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class EmailRecipient(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(), nullable=False)
    name = db.Column(db.String())

    notification_template_id = db.Column(db.Integer, db.ForeignKey("notification_template.id"))

    def __init__(self, email, name):
        self.id = None
        self.email = email
        self.name = name


class NotificationTemplate(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    message_title = db.Column(db.String())
    message_body = db.Column(db.String())

    recipients = db.relationship("EmailRecipient", cascade="all, delete-orphan")

    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization = db.relationship("Organization")

    def __init__(self, name, description, message_title, message_body, recipients, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.message_title = message_title
        self.message_body = message_body
        self.recipients = recipients

    @classmethod
    def get_by_filter(cls, search, organization):
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
        templates, count = cls.get_by_filter(search, user.organization)
        items = [template.to_dict() for template in templates]
        return {"total_count": count, "items": items}

    @classmethod
    def add(cls, user, data) -> tuple[str, int]:
        template = cls.from_dict(data)
        template.organization = user.organization
        db.session.add(template)
        db.session.commit()
        return f"created {template.id}", 201

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["recipients"] = [recipient.id for recipient in self.recipients]
        data["tag"] = "mdi-email-outline"
        return data
