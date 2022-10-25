"""added default user accounts and permissions

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


class PermissionREVac311a84207a(Base):
    __tablename__ = 'permission'
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(session, id, name, description):
        result = session.query(PermissionREVac311a84207a).filter_by(id=id).first()
        if not result:
            session.add(PermissionREVac311a84207a(id, name, description))


class RoleREVac311a84207a(Base):
    __tablename__ = 'role'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    description = sa.Column(sa.String())
    permissions = orm.relationship(PermissionREVac311a84207a, secondary='role_permission')

    def __init__(self, name, description, permissions=None):
        if not permissions:
            permissions = []
        self.id = None
        self.name = name
        self.description = description
        self.permissions = permissions


class RolePermissionREVac311a84207a(Base):
    __tablename__ = 'role_permission'
    role_id = sa.Column(sa.Integer, sa.ForeignKey('role.id'), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey('permission.id'), primary_key=True)

    def __init__(self, role_id, permission_id):
        self.role_id = role_id
        self.permission_id = permission_id


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

    # add all default permissions
    
    PermissionREVac311a84207a.add(session, "ANALYZE_ACCESS", "Analyze access", "Access to Analyze module")
    PermissionREVac311a84207a.add(session, "ANALYZE_CREATE", "Analyze create", "Create report item")
    PermissionREVac311a84207a.add(session, "ANALYZE_UPDATE", "Analyze update", "Update report item")
    PermissionREVac311a84207a.add(session, "ANALYZE_DELETE", "Analyze delete", "Delete report item")
    PermissionREVac311a84207a.add(session, "ASSESS_ACCESS", "Assess access", "Access to Assess module")
    PermissionREVac311a84207a.add(session, "ASSESS_CREATE", "Assess create", "Create news item")
    PermissionREVac311a84207a.add(session, "ASSESS_UPDATE", "Assess update", "Update news item")
    PermissionREVac311a84207a.add(session, "ASSESS_DELETE", "Assess delete", "Delete news item")
    PermissionREVac311a84207a.add(session, "MY_ASSETS_ACCESS", "My Assets access", "Access to My Assets module")
    PermissionREVac311a84207a.add(session, "MY_ASSETS_CREATE", "My Assets create", "Creation of products in My Assets module")
    PermissionREVac311a84207a.add(session, "MY_ASSETS_CONFIG", "My Assets config", "Configuration of access and groups in My Assets module")
    PermissionREVac311a84207a.add(session, "CONFIG_ACCESS", "Configuration access", "Access to Configuration module")
    PermissionREVac311a84207a.add(session, "CONFIG_ORGANIZATION_ACCESS", "Config organizations access", "Access to attributes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ORGANIZATION_CREATE", "Config organization create", "Create organization configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ORGANIZATION_UPDATE", "Config organization update", "Update organization configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ORGANIZATION_DELETE", "Config organization delete", "Delete organization configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_USER_ACCESS", "Config users access", "Access to users configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_USER_CREATE", "Config user create", "Create user configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_USER_UPDATE", "Config user update", "Update user configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_USER_DELETE", "Config user delete", "Delete user configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ROLE_CREATE", "Config role create", "Create role configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRODUCT_TYPE_ACCESS", "Config product types access", "Access to product types configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRODUCT_TYPE_CREATE", "Config product type create", "Create product type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRODUCT_TYPE_UPDATE", "Config product type update", "Update product type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRODUCT_TYPE_DELETE", "Config product type delete", "Delete product type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ATTRIBUTE_ACCESS", "Config attributes access", "Access to attributes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ATTRIBUTE_CREATE", "Config attribute create", "Create attribute configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ATTRIBUTE_UPDATE", "Config attribute update", "Update attribute configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_ATTRIBUTE_DELETE", "Config attribute delete", "Delete attribute configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REPORT_TYPE_ACCESS", "Config report item types access", "Access to report item types configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REPORT_TYPE_CREATE", "Config report item type create", "Create report item type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REPORT_TYPE_UPDATE", "Config report item type update", "Update report item type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REPORT_TYPE_DELETE", "Config report item type delete", "Delete report item type configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_COLLECTORS_NODE_ACCESS", "Config collectors nodes access", "Access to collectors nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_COLLECTORS_NODE_CREATE", "Config collectors node create", "Create collectors node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_COLLECTORS_NODE_UPDATE", "Config collectors node update", "Update collectors node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_COLLECTORS_NODE_DELETE", "Config collectors node delete", "Delete collectors node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_ACCESS", "Config OSINT source access", "Access to OSINT sources configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_CREATE", "Config OSINT source create", "Create OSINT source configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_UPDATE", "Config OSINT source update", "Update OSINT source configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_DELETE", "Config OSINT source delete", "Delete OSINT source configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_GROUP_ACCESS", "Config OSINT source group access", "Access to OSINT sources groups configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_GROUP_CREATE", "Config OSINT source group create", "Create OSINT source group configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_GROUP_UPDATE", "Config OSINT source group update", "Update OSINT source group configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_OSINT_SOURCE_GROUP_DELETE", "Config OSINT source group delete", "Delete OSINT source group configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_ACCESS_ACCESS", "Config remote access access", "Access to remote access configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_ACCESS_CREATE", "Config remote access create", "Create remote access configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_ACCESS_UPDATE", "Config remote access update", "Update remote access configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_ACCESS_DELETE", "Config remote access delete", "Delete remote access configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_NODE_ACCESS", "Config remote nodes access", "Access to remote nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_NODE_CREATE", "Config remote node create", "Create remote node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_NODE_UPDATE", "Config remote node update", "Update remote node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_REMOTE_NODE_DELETE", "Config remote node delete", "Delete remote node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access", "Access to presenters nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create", "Create presenters node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update", "Update presenters node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete", "Delete presenters node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access", "Access to publishers nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create", "Create publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update", "Update publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete", "Delete publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access", "Access to publisher presets configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create", "Create publisher preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update", "Update publisher preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete", "Delete publisher preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOTS_NODE_ACCESS", "Config bots nodes access", "Access to bots nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOTS_NODE_CREATE", "Config bots node create", "Create bots node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOTS_NODE_UPDATE", "Config bots node update", "Update bots node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOTS_NODE_DELETE", "Config bots node delete", "Delete bots node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOT_PRESET_ACCESS", "Config bot presets access", "Access to bot presets configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOT_PRESET_CREATE", "Config bot preset create", "Create bot preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOT_PRESET_UPDATE", "Config bot preset update", "Update bot preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_BOT_PRESET_DELETE", "Config bot preset delete", "Delete bot preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access", "Access to presenters nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create", "Create presenters node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update", "Update presenters node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete", "Delete presenters node configuration")
    PermissionREVac311a84207a.add(session, "PUBLISH_ACCESS", "Publish access", "Access to publish module")
    PermissionREVac311a84207a.add(session, "PUBLISH_CREATE", "Publish create", "Create product")
    PermissionREVac311a84207a.add(session, "PUBLISH_UPDATE", "Publish update", "Update product")
    PermissionREVac311a84207a.add(session, "PUBLISH_DELETE", "Publish delete", "Delete product")
    PermissionREVac311a84207a.add(session, "PUBLISH_PRODUCT", "Publish product", "Publish product")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access", "Access to publishers nodes configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create", "Create publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update", "Update publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete", "Delete publishers node configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access", "Access to publisher presets configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create", "Create publisher preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update", "Update publisher preset configuration")
    PermissionREVac311a84207a.add(session, "CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete", "Delete publisher preset configuration")
    session.commit()

    role = session.query(RoleREVac311a84207a).filter_by(name="Admin").first()

    if role:
        role.permissions = session.query(PermissionREVac311a84207a).all()
        session.add(role)
        session.commit()


    # Admin user account

    user = session.query(UserREVac311a84207a).filter_by(username="admin").first()

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
