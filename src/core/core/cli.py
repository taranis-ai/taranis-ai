import sys
from collections.abc import Sequence
from datetime import timedelta
from typing import cast

import click

from core import create_app
from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
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


def backfill_fuzzy_hashes(days: int, batch_size: int) -> tuple[int, int]:
    now = NewsItem.utcnow()
    last_id = ""
    scanned = hashed = 0
    while rows := db.session.execute(
        db.select(NewsItem.id, NewsItem.content)
        .where(
            NewsItem.id > last_id,
            NewsItem.fuzzy_hash.is_(None),
            NewsItem.collected >= now - timedelta(days=days),
            NewsItem.collected <= now,
        )
        .order_by(NewsItem.id)
        .limit(batch_size)
        .with_for_update()
    ).all():
        for item_id, content in rows:
            if fingerprint := NewsItem.get_fuzzy_hash(content):
                db.session.execute(db.update(NewsItem).where(NewsItem.id == item_id).values(fuzzy_hash=fingerprint, updated=NewsItem.updated))
                hashed += 1
        scanned += len(rows)
        last_id = rows[-1].id
        db.session.commit()
    return scanned, hashed


@main.command("backfill-fuzzy-hashes")
@click.option("--days", type=click.IntRange(1, 365), default=None, help="Collection window; defaults to FUZZY_DEDUP_LOOKBACK_DAYS.")
@click.option("--batch-size", type=click.IntRange(1, 5000), default=500, show_default=True)
def backfill_fuzzy_hashes_command(days: int | None, batch_size: int) -> None:
    """Fill missing fingerprints without deleting items or changing timestamps."""
    app = create_app(initial_setup=False)
    with app.app_context():
        try:
            scanned, hashed = backfill_fuzzy_hashes(days or Config.FUZZY_DEDUP_LOOKBACK_DAYS, batch_size)
        except Exception:
            db.session.rollback()
            logger.exception("Fuzzy hash backfill failed")
            raise click.ClickException("Fuzzy hash backfill failed; see core logs. Rerun to resume committed batches.") from None
    click.echo(f"Scanned {scanned} items; filled {hashed} fingerprints; skipped {scanned - hashed} short or empty bodies.")


if __name__ == "__main__":
    main()
