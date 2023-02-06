from marshmallow import post_load, fields
from sqlalchemy import func, or_, orm

from core.managers.db_manager import db
from core.model.address import NewAddressSchema
from shared.schema.organization import OrganizationSchema, OrganizationPresentationSchema


class NewOrganizationSchema(OrganizationSchema):
    address = fields.Nested(NewAddressSchema)

    @post_load
    def make(self, data, **kwargs):
        return Organization(**data)


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    address = db.relationship("Address", cascade="all")

    def __init__(self, name, description, address, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.address = address
        self.tag = "mdi-office-building"

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-office-building"

    @classmethod
    def find(cls, organization_id):
        return cls.query.get(organization_id)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Organization.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Organization.name).like(search_string),
                    func.lower(Organization.description).like(search_string),
                )
            )

        return query.order_by(db.asc(Organization.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        organizations, count = cls.get(search)
        organizations_schema = OrganizationPresentationSchema(many=True)
        return {"total_count": count, "items": organizations_schema.dump(organizations)}

    @classmethod
    def add_new(cls, data):
        new_organization_schema = NewOrganizationSchema()
        organization = new_organization_schema.load(data, partial=True)
        db.session.add(organization.address)
        db.session.add(organization)
        db.session.commit()

    @classmethod
    def update(cls, organization_id, data):
        schema = NewOrganizationSchema()
        updated_organization = schema.load(data)
        organization = cls.query.get(organization_id)
        organization.name = updated_organization.name
        organization.description = updated_organization.description
        organization.address.street = updated_organization.address.street
        organization.address.city = updated_organization.address.city
        organization.address.zip = updated_organization.address.zip
        organization.address.country = updated_organization.address.country
        db.session.commit()

    @classmethod
    def delete(cls, id):
        organization = cls.query.get(id)
        db.session.delete(organization)
        db.session.commit()
