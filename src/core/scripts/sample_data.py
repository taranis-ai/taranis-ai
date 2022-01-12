import sys
from sqlalchemy.exc import IntegrityError

from managers import db_manager
from model.role import Role
from model.permission import Permission
from model.user import User
from model.address import Address
from model.organization import Organization


def main(db):
    user_role = Role(None, 'User', 'Test user role', [])
    user_role.permissions.append(Permission.find("ASSESS_ACCESS"))
    user_role.permissions.append(Permission.find("ASSESS_CREATE"))
    user_role.permissions.append(Permission.find("ASSESS_UPDATE"))
    user_role.permissions.append(Permission.find("ASSESS_DELETE"))
    user_role.permissions.append(Permission.find("ANALYZE_ACCESS"))
    user_role.permissions.append(Permission.find("ANALYZE_CREATE"))
    user_role.permissions.append(Permission.find("ANALYZE_UPDATE"))
    user_role.permissions.append(Permission.find("ANALYZE_DELETE"))
    user_role.permissions.append(Permission.find("PUBLISH_ACCESS"))
    user_role.permissions.append(Permission.find("PUBLISH_CREATE"))
    user_role.permissions.append(Permission.find("PUBLISH_UPDATE"))
    user_role.permissions.append(Permission.find("PUBLISH_DELETE"))
    user_role.permissions.append(Permission.find("PUBLISH_PRODUCT"))
    db.session.add(user_role)

    address = Address("Budatinska 30", "Bratislava", "851 06", "Slovakia")
    organization = Organization(None, "SK-CERT", "", address)
    db.session.add(organization)

    role = Role.find_by_name('User')

    user = User(None, 'user', 'Test User', [], [], [])
    user.roles.append(role)
    user.organizations.append(organization)

    db.session.add(user)
    db.session.commit()

    role = Role.find_by_name('Admin')

    user = User(None, 'admin', 'Test Administrator', [], [], [])
    user.roles.append(role)
    user.organizations.append(organization)
    db.session.add(user)

    user = User(None, 'customer', 'Test Customer', [], [], [])
    user.permissions.append(Permission.find("MY_ASSETS_ACCESS"))
    user.permissions.append(Permission.find("MY_ASSETS_CREATE"))
    user.permissions.append(Permission.find("MY_ASSETS_CONFIG"))
    user.organizations.append(organization)
    db.session.add(user)


def run(db):
    try:
        main(db_manager.db)
    except IntegrityError as exc:
        print(exc, file=sys.stderr)
        print('Detected UniqueViolation exception. Probably the '
              'sample data has already been imported. If not, please report '
              'this as bug.', file=sys.stderr)


if __name__ == '__main__':
    run(db_manager.db)
    sys.exit()
