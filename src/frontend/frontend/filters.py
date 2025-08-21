from jinja2 import pass_context
from flask import url_for, render_template
import base64
from heroicons.jinja import heroicon_outline

from markupsafe import Markup
from models.admin import OSINTSource
from models.types import OSINTState

__all__ = [
    "human_readable_trigger",
    "last_path_segment",
    "admin_action",
    "get_var",
    "b64decode",
    "render_state",
    "render_truncated",
    "render_icon",
    "render_parameter",
    "render_count",
    "render_source_parameter",
    "render_item_type",
]


def parse_interval_trigger(trigger):
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


def human_readable_trigger(trigger):
    if trigger and trigger.startswith("interval"):
        return parse_interval_trigger(trigger)

    return trigger


def render_count(item, field: str) -> int:
    if hasattr(item, field) and isinstance(getattr(item, field), list):
        return len(getattr(item, field))
    return 0


def render_icon(item: OSINTSource) -> str:
    if hasattr(item, "icon") and item.icon:
        # TODO: Check if this is safe to render
        return Markup(f"<img src='data:image/svg+xml;base64,{item.icon}' height='32px' width='32px'  class='icon' alt='Icon' />")
    if hasattr(item, "type") and item.type:
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
    source_parameter = ""
    if hasattr(item, "parameters") and isinstance(item.parameters, dict):
        if item.type in ["rss_collector", "simple_web_collector"]:
            source_parameter = item.parameters.get("FEED_URL", "")
        if item.type == "misp_collector":
            source_parameter = item.parameters.get("URL", "")
    return source_parameter


def render_state(item: OSINTSource) -> str:
    if hasattr(item, "state"):
        if item.state == OSINTState.NOT_MODIFIED:
            state_message = (
                f"Last collected: {item.last_collected.strftime('%Y-%m-%d %H:%M:%S')}"
                if (hasattr(item, "last_collected") and item.last_collected)
                else ""
            )
        else:
            state_message = item.last_error_message or ""
        return Markup(render_template("partials/state_badge.html", state=item.state, state_message=state_message))
    return Markup(render_template("partials/state_badge.html", state=-1))


def render_truncated(item, field: str) -> str:
    if hasattr(item, field) and isinstance(getattr(item, field), str):
        value = getattr(item, field)
        return Markup(f"<div class='truncate'>{value}</div>")
    return Markup("<div class='truncate max-w-[50ch]'>N/A</div>")


def render_item_type(item) -> str:
    if hasattr(item, "type") and item.type:
        return item.type.split("_")[0].capitalize()
    return "Unknown"


def render_worker_status(item) -> str:
    if hasattr(item, "status") and item.status:
        return Markup(render_template("partials/status_badge.html", status=item.status))
    return Markup(render_template("partials/status_badge.html"))


def last_path_segment(value):
    return value.strip("/").split("/")[-1]


def admin_action(value):
    return url_for("admin_settings.settings_action", action=last_path_segment(value))


def b64decode(value):
    return base64.b64decode(value).decode("utf-8")


@pass_context
def get_var(ctx, name):
    return ctx.get(name)
