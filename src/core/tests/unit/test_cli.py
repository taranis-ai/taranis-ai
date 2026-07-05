import click
from werkzeug.security import check_password_hash

from core.cli import set_user_password, set_user_roles
from core.model.role import Role
from core.model.user import User


def test_set_user_password_updates_existing_user(app, session):
    with app.app_context():
        set_user_password("user", "new-test-password")

        user = User.find_by_name("user")
        assert user is not None
        assert user.password is not None
        assert check_password_hash(user.password, "new-test-password")


def test_set_user_roles_replaces_existing_roles(app, session):
    with app.app_context():
        admin_role = Role.filter_by_name("Admin")
        assert admin_role is not None

        assigned_roles = set_user_roles("user", ("Admin", admin_role.id))

        user = User.find_by_name("user")
        assert user is not None
        assert assigned_roles == [admin_role]
        assert user.roles == [admin_role]


def test_set_user_roles_rejects_missing_role(app, session):
    with app.app_context():
        try:
            set_user_roles("user", ("missing-role",))
        except click.ClickException as exc:
            assert "Role 'missing-role' not found" == exc.message
        else:
            raise AssertionError("missing role should fail")
