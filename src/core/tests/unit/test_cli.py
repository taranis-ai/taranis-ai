import click
import pytest
from click.testing import CliRunner
from werkzeug.security import check_password_hash

from core.cli import main, set_user_password, set_user_roles
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
        with pytest.raises(click.ClickException, match=r"Role 'missing-role' not found"):
            set_user_roles("user", ("missing-role",))


def test_set_password_stdin_rejects_empty_input():
    result = CliRunner().invoke(main, ("set-password", "user", "--password-stdin"), input="")

    assert result.exit_code != 0
    assert "No password read from stdin" in result.output
