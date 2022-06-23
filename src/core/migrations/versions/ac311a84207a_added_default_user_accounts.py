"""added default user accounts

Revision ID: ac311a84207a
Revises: dc12ca6eddba
Create Date: 2022-07-01 20:12:38.716047

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# revision identifiers, used by Alembic.
revision = 'ac311a84207a'
down_revision = 'dc12ca6eddba'
branch_labels = None
depends_on = None


class UserREVac311a84207a(Base):
    __tablename__ = 'user'
    id = sa.Column(sa.Integer, primary_key=True)
    username = sa.Column(sa.String(64), unique=True, nullable=False)
    name = sa.Column(sa.String(), nullable=False)
    profile_id = sa.Column(sa.Integer, sa.ForeignKey('user_profile.id'))

    def __init__(self, username, name, profile_id):
        self.id = None
        self.username = username
        self.name = name
        self.profile_id = profile_id


class UserOrganizationREVac311a84207a(Base):
    __tablename__ = 'user_organization'
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), primary_key=True)
    organization_id = sa.Column(sa.Integer, sa.ForeignKey('organization.id'), primary_key=True)

    def __init__(self, user_id, organization_id):
        self.user_id = user_id
        self.organization_id = organization_id


class UserRoleREVac311a84207a(Base):
    __tablename__ = 'user_role'
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), primary_key=True)
    role_id = sa.Column(sa.Integer, sa.ForeignKey('role.id'), primary_key=True)

    def __init__(self, user_id, role_id):
        self.user_id = user_id
        self.role_id = role_id


class UserProfileREVac311a84207a(Base):
    __tablename__ = 'user_profile'
    id = sa.Column(sa.Integer, primary_key=True)
    spellcheck = sa.Column(sa.Boolean, default=True)
    dark_theme = sa.Column(sa.Boolean, default=False)

    def __init__(self, spellcheck, dark_theme):
        self.id = None
        self.spellcheck = spellcheck
        self.dark_theme = dark_theme
        self.hotkeys = []
        self.word_lists = []


class RoleREVac311a84207a(Base):
    __tablename__ = 'role'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(self, name, description):
        self.id = None
        self.name = name
        self.description = description


class RolePermissionREVac311a84207a(Base):
    __tablename__ = 'role_permission'
    role_id = sa.Column(sa.Integer, sa.ForeignKey('role.id'), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey('permission.id'), primary_key=True)

    def __init__(self, role_id, permission_id):
        self.role_id = role_id
        self.permission_id = permission_id


class PermissionREVac311a84207a(Base):
    __tablename__ = 'permission'
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())


class AddressREVac311a84207a(Base):
    __tablename__ = 'address'
    id = sa.Column(sa.Integer, primary_key=True)
    street = sa.Column(sa.String())
    city = sa.Column(sa.String())
    zip = sa.Column(sa.String())
    country = sa.Column(sa.String())

    def __init__(self, street, city, zip, country):
        self.id = None
        self.street = street
        self.city = city
        self.zip = zip
        self.country = country


class OrganizationREVac311a84207a(Base):
    __tablename__ = 'organization'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String())
    address_id = sa.Column(sa.Integer, sa.ForeignKey('address.id'))

    def __init__(self, name, description, address_id):
        self.id = None
        self.name = name
        self.description = description
        self.address_id = address_id


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # Admin user account

    user = session.query(UserREVac311a84207a).filter_by(username="admin").first()
    role = session.query(RoleREVac311a84207a).filter_by(name="Admin").first()

    if not user and role:
        address = AddressREVac311a84207a('29 Arlington Avenue', 'Islington, London', 'N1 7BE', 'United Kingdom')
        session.add(address)
        session.commit()

        organization = OrganizationREVac311a84207a('The Earth', 'Earth is the third planet from the Sun and the only astronomical object known to harbor life.', address.id)
        session.add(organization)
        session.commit()

        profile = UserProfileREVac311a84207a(True, False)
        session.add(profile)
        session.commit()

        user = UserREVac311a84207a('admin', 'Arthur Dent', profile.id)
        session.add(user)
        session.commit()

        session.add(UserOrganizationREVac311a84207a(user.id, organization.id))
        session.add(UserRoleREVac311a84207a(user.id, role.id))
        session.commit()

    # Basic user account

    user = session.query(UserREVac311a84207a).filter_by(username="user").first()
    role = session.query(RoleREVac311a84207a).filter_by(name="User").first()

    if not user:
        if not role:
            role = RoleREVac311a84207a('User', 'Basic user role')
            session.add(role)
            session.commit()

            session.add(RolePermissionREVac311a84207a(role.id, 'ASSESS_ACCESS'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ASSESS_CREATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ASSESS_UPDATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ASSESS_DELETE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ANALYZE_ACCESS'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ANALYZE_CREATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ANALYZE_UPDATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'ANALYZE_DELETE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'PUBLISH_ACCESS'))
            session.add(RolePermissionREVac311a84207a(role.id, 'PUBLISH_CREATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'PUBLISH_UPDATE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'PUBLISH_DELETE'))
            session.add(RolePermissionREVac311a84207a(role.id, 'PUBLISH_PRODUCT'))

            session.commit()

        address = AddressREVac311a84207a('Cherry Tree Rd', 'Beaconsfield, Buckinghamshire', 'HP9 1BH', 'United Kingdom')
        session.add(address)
        session.commit()

        organization = OrganizationREVac311a84207a('The Clacks', 'A network infrastructure of Semaphore Towers, that operate in a similar fashion to telegraph.', address.id)
        session.add(organization)
        session.commit()

        profile = UserProfileREVac311a84207a(True, False)
        session.add(profile)
        session.commit()

        user = UserREVac311a84207a('user', 'Terry Pratchett', profile.id)
        session.add(user)
        session.commit()

        session.add(UserOrganizationREVac311a84207a(user.id, organization.id))
        session.add(UserRoleREVac311a84207a(user.id, role.id))
        session.commit()


def downgrade():
    pass
