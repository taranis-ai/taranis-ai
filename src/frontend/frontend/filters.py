import base64
from datetime import datetime
from typing import Any

import filetype
from flask import render_template, url_for
from heroicons.jinja import heroicon_outline
from jinja2 import pass_context
from markupsafe import Markup, escape
from models.admin import OSINTSource
from models.assess import Story


__all__ = [
    "human_readable_trigger",
    "last_path_segment",
    "admin_action",
    "get_var",
    "b64decode",
    "render_truncated",
    "render_icon",
    "render_parameter",
    "render_count",
    "render_source_parameter",
    "render_item_type",
    "render_validation_status",
    "render_item_validation_status",
    "badge_class",
    "badge_label",
    "normalize_validation_status",
    "render_worker_status",
    "format_datetime",
    "get_published_dates",
]


def badge_class(status: str) -> str:
    """Return the CSS class for a badge based on validation status."""
    if status == "valid":
        return "badge-success"
    elif status == "invalid":
        return "badge-error"
    return "badge-neutral"


def badge_label(status: str) -> str:
    """Return the label for a badge based on validation status."""
    if status == "valid":
        return "Valid"
    elif status == "invalid":
        return "Invalid"
    return "Unknown"


def normalize_validation_status(status: dict[str, Any] | None) -> str:
    """Normalize to 'valid' | 'invalid' | 'unknown'.
    Expected input: dict with key 'is_valid' or None. Any other type -> 'unknown'.
    """
    if isinstance(status, dict):
        is_valid = status.get("is_valid")
        if is_valid is True:
            return "valid"
        if is_valid is False:
            return "invalid"
    return "unknown"


def parse_interval_trigger(trigger: str) -> str:
    time_part = trigger.split("[")[1].rstrip("]")
    hours, minutes, seconds = map(int, time_part.split(":"))
    parts: list[str] = []
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


def _guess_mime_pure_py(b64: str) -> str:
    raw = base64.b64decode(b64)
    kind = filetype.guess(raw)
    return kind.mime if kind else "application/octet-stream"


def render_icon(item: OSINTSource) -> str:
    if hasattr(item, "icon") and item.icon:
        # TODO: Check if this is safe to render
        _mime = _guess_mime_pure_py(item.icon)
        return Markup(f"<img src='data:{_mime};base64,{item.icon}' height='32px' width='32px'  class='icon' alt='Icon' />")
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
        if item.type in ["rss_collector"]:
            source_parameter = item.parameters.get("FEED_URL", "")
        if item.type == "simple_web_collector":
            source_parameter = item.parameters.get("WEB_URL", "")
        if item.type == "misp_collector":
            source_parameter = item.parameters.get("URL", "")
    return source_parameter


def render_truncated(item, field: str) -> str:
    if hasattr(item, field) and isinstance(getattr(item, field), str):
        value = getattr(item, field)
        return Markup(f"<div class='truncate'>{value}</div>")
    return Markup("<div class='truncate max-w-[50ch]'>N/A</div>")


def render_item_type(item) -> str:
    if hasattr(item, "type") and item.type:
        return item.type.split("_")[0].capitalize()
    return "Unknown"


def render_datetime(item, field: str) -> str:
    if hasattr(item, field) and getattr(item, field):
        value = getattr(item, field)
        return format_datetime(value)
    return "N/A"


def render_worker_status(item) -> str:
    enabled = item.enabled if hasattr(item, "enabled") else True
    status = item.status if hasattr(item, "status") else None
    return Markup(render_template("partials/status_badge.html", status=status, enabled=enabled))


def last_path_segment(value: str) -> str:
    return value.strip("/").split("/")[-1]


def admin_action(value: str) -> str:
    return url_for("admin_settings.settings_action", action=last_path_segment(value))


def b64decode(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


def render_validation_status(status: dict[str, Any] | None) -> str:
    """Render validation status badge for a status dict.
    Expected: dict with keys is_valid, error_type?, error_message?; anything else -> Unknown.
    """
    if isinstance(status, dict):
        is_valid = status.get("is_valid")
        error_type = status.get("error_type") or ""
        error_message = status.get("error_message") or ""
        if is_valid is True:
            return Markup('<span class="badge badge-success text-xs">Valid</span>')
        if is_valid is False:
            et = escape(error_type)
            em = escape(error_message)
            tooltip_attr = f'title="{et}: {em}"' if em else f'title="{et}"'
            return Markup(f'<span class="badge badge-error text-xs" {tooltip_attr}>Invalid</span>')
    return Markup('<span class="badge badge-neutral text-xs">Unknown</span>')


def render_item_validation_status(item) -> str:
    """Adapter for table renderers: extract item.validation_status and render."""
    status = None
    if isinstance(item, dict):
        status = item.get("validation_status")
    elif hasattr(item, "validation_status"):
        status = getattr(item, "validation_status")
    return render_validation_status(status)


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime):
        return value.strftime("%d. %B %Y %H:%M")
    return value


def get_published_dates(story: Story) -> dict[str, datetime | None]:
    published = {}
    if not story.news_items:
        return {"earliest": story.created, "latest": story.updated}
    for news_item in story.news_items:
        if published_at := news_item.published or news_item.collected:
            published["earliest"] = published.get("earliest", published_at)
            published["latest"] = published.get("latest", published_at)
            if published_at < published["earliest"]:
                published["earliest"] = published_at
            if published_at > published["latest"]:
                published["latest"] = published_at
    return published


@pass_context
def get_var(ctx, name):
    return ctx.get(name)
