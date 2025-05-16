from jinja2 import pass_context
from flask import url_for
import base64

from models.admin import Role

__all__ = ["human_readable_trigger", "last_path_segment", "admin_action", "get_var", "permissions_count", "b64decode"]


def human_readable_trigger(trigger):
    if not trigger.startswith("interval"):
        return trigger

    time_part = trigger.split("[")[1].rstrip("]")
    hours, minutes, seconds = map(int, time_part.split(":"))
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    return "every " + ", ".join(parts)


def permissions_count(role: Role):
    return len(role.permissions)


def last_path_segment(value):
    return value.strip("/").split("/")[-1]


def admin_action(value):
    return url_for("admin_settings.settings_action", action=last_path_segment(value))


def b64decode(value):
    return base64.b64decode(value).decode("utf-8")


@pass_context
def get_var(ctx, name):
    return ctx.get(name)
