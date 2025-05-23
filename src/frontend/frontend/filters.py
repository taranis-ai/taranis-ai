from jinja2 import pass_context
from flask import url_for, render_template
import base64
from heroicons.jinja import heroicon_outline

from markupsafe import Markup
from models.admin import Role, User, OSINTSource
from frontend.log import logger

__all__ = [
    "human_readable_trigger",
    "last_path_segment",
    "admin_action",
    "get_var",
    "permissions_count",
    "role_count",
    "b64decode",
    "render_state",
    "render_icon",
    "render_parameter",
    "render_source_parameter",
]


def parse_interval_trigger(trigger):
    time_part = trigger.split("[")[1].rstrip("]")
    hours, minutes, seconds = map(int, time_part.split(":"))
    logger.debug(f"Trigger time part: {time_part}, hours: {hours}, minutes: {minutes}, seconds: {seconds} --- {trigger}")
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    return "every " + ", ".join(parts)


def human_readable_trigger(trigger):
    if trigger.startswith("interval"):
        return parse_interval_trigger(trigger)

    return trigger


def permissions_count(item: Role | User) -> int:
    if hasattr(item, "permissions") and isinstance(item.permissions, list):
        return len(item.permissions)
    return 0


def role_count(item: User) -> int:
    if hasattr(item, "roles") and isinstance(item.roles, list):
        return len(item.roles)
    return 0


def render_icon(item: OSINTSource) -> str:
    if hasattr(item, "icon") and item.icon:
        # TODO: Check if this is safe to render
        return Markup(f"<img src='data:image/svg+xml;base64,{item.icon}' height='32px' width='32px'  class='icon' alt='Icon' />")
    if item.type == "rss_collector":
        return heroicon_outline("rss")
    if item.type == "simple_web_collector":
        return heroicon_outline("globe-alt")
    if item.type == "misp_collector":
        return Markup(render_template("partials/misp_logo.html"))
    return heroicon_outline("question-mark-circle")


def render_parameter(item, key):
    if hasattr(item, "parameters") and isinstance(item.parameters, dict):
        return item.parameters.get(key)
    return None


def render_source_parameter(item: OSINTSource) -> str:
    if hasattr(item, "parameters") and isinstance(item.parameters, dict):
        if item.type in ["rss_collector", "simple_web_collector"]:
            return item.parameters.get("FEED_URL", "")
        if item.type == "misp_collector":
            return item.parameters.get("URL", "")
    return ""


def render_state(item) -> str:
    if hasattr(item, "state"):
        return Markup(
            render_template(
                "partials/state_badge.html",
                state=item.state,
            )
        )
    return Markup(render_template("partials/state_badge.html", state=-1))


def last_path_segment(value):
    return value.strip("/").split("/")[-1]


def admin_action(value):
    return url_for("admin_settings.settings_action", action=last_path_segment(value))


def b64decode(value):
    return base64.b64decode(value).decode("utf-8")


@pass_context
def get_var(ctx, name):
    return ctx.get(name)
