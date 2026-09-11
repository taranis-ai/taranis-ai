import sys
from collections.abc import Sequence
from typing import cast

import click

from core import create_app
from core.managers.db_manager import db
from core.model.role import Role
from core.model.user import User


def _role_by_name_or_id(role_ref: str) -> Role | None:
    return Role.filter_by_name(role_ref) or Role.get(role_ref)


def set_user_password(username: str, password: str) -> None:
    if not password:
        raise click.ClickException("Password must not be empty")
    user = User.find_by_name(username)
    if not user:
        raise click.ClickException(f"User '{username}' not found")
    user.change_password(password)


def set_user_roles(username: str, role_refs: Sequence[str]) -> list[Role]:
    if not role_refs:
        raise click.ClickException("At least one role is required")
    user = User.find_by_name(username)
    if not user:
        raise click.ClickException(f"User '{username}' not found")

    roles: list[Role] = []
    role_ids: set[str] = set()
    for role_ref in role_refs:
        role = _role_by_name_or_id(role_ref)
        if not role:
            raise click.ClickException(f"Role '{role_ref}' not found")
        if role.id not in role_ids:
            roles.append(role)
            role_ids.add(role.id)

    user.roles = roles
    db.session.commit()
    return roles


@click.group()
def main() -> None:
    """Operational Taranis AI commands."""


@main.command("set-password")
@click.argument("username")
@click.option("--password", help="New password. Prefer the prompt or --password-stdin.")
@click.option("--password-stdin", is_flag=True, help="Read the new password from stdin.")
def set_password_command(username: str, password: str | None, password_stdin: bool) -> None:
    if password is not None and password_stdin:
        raise click.UsageError("Use either --password or --password-stdin, not both")
    if password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise click.UsageError("No password read from stdin")
    if password is None:
        password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    password = cast(str, password)

    app = create_app(initial_setup=False)
    with app.app_context():
        set_user_password(username, password)

    click.echo(f"Updated password for user '{username}'")


@main.command("set-roles")
@click.argument("username")
@click.argument("roles", nargs=-1, required=True)
def set_roles_command(username: str, roles: tuple[str, ...]) -> None:
    app = create_app(initial_setup=False)
    with app.app_context():
        assigned_roles = set_user_roles(username, roles)
        assigned_role_names = ", ".join(role.name for role in assigned_roles)

    click.echo(f"Updated roles for user '{username}': {assigned_role_names}")


if __name__ == "__main__":
    main()
