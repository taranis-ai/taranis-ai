from jinja2 import pass_context
from flask import url_for

from frontend.log import logger

__all__ = ["human_readable_trigger", "last_path_segment", "admin_action", "get_var"]


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


def last_path_segment(value):
    return value.strip("/").split("/")[-1]


def admin_action(value):
    return url_for("admin_settings.settings_action", action=last_path_segment(value))


@pass_context
def get_var(ctx, name):
    logger.debug(f"get_var: {name}")
    logger.debug(f"ctx: {ctx.get(name)}")
    return ctx.get(name)
