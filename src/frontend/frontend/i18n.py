from functools import cache
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask import Flask, current_app, g, request
from flask_babel import Babel, get_locale, get_timezone, gettext
from flask_jwt_extended import current_user


babel = Babel()


def _supported_locales() -> list[str]:
    return list(current_app.config.get("BABEL_SUPPORTED_LOCALES", ["en"]))


def _default_locale() -> str:
    return str(current_app.config.get("BABEL_DEFAULT_LOCALE", "en"))


def _default_timezone() -> str:
    return str(current_app.config.get("BABEL_DEFAULT_TIMEZONE", "UTC"))


def _profile_value(user: Any, key: str) -> str | None:
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    if isinstance(profile, dict):
        value = profile.get(key)
    else:
        value = getattr(profile, key, None)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _profile_language(user: Any) -> str | None:
    language = _profile_value(user, "language")
    return language.lower() if language else None


def _valid_timezone(timezone_name: str | None) -> str | None:
    if not timezone_name:
        return None
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None
    return timezone_name


def _accepted_locale() -> str | None:
    supported_locales = _supported_locales()
    for locale, _quality in request.accept_languages:
        normalized_locale = locale.lower()
        if normalized_locale in supported_locales:
            return normalized_locale
        primary_locale = normalized_locale.split("-", 1)[0]
        if primary_locale in supported_locales:
            return primary_locale

    return None


def _current_request_user() -> Any | None:
    if getattr(g, "skip_current_user_injection", False):
        return None

    try:
        return current_user if current_user else None
    except RuntimeError:
        return None


def select_locale() -> str:
    supported_locales = _supported_locales()
    default_locale = _default_locale()

    if user := _current_request_user():
        language = _profile_language(user)
        if language in supported_locales:
            return language

    return _accepted_locale() or default_locale


def select_timezone() -> str:
    if user := _current_request_user():
        if timezone_name := _valid_timezone(_profile_value(user, "timezone")):
            return timezone_name

    return _default_timezone()


def get_supported_language_options() -> list[dict[str, str]]:
    names = {
        "en": gettext("English"),
        "de": gettext("German"),
    }
    return [{"id": locale, "name": names.get(locale, locale)} for locale in _supported_locales()]


@cache
def get_timezone_options() -> list[str]:
    return sorted(available_timezones())


def init(app: Flask) -> None:
    babel.init_app(
        app,
        default_locale=app.config["BABEL_DEFAULT_LOCALE"],
        default_timezone=app.config["BABEL_DEFAULT_TIMEZONE"],
        default_translation_directories=app.config["BABEL_TRANSLATION_DIRECTORIES"],
        locale_selector=select_locale,
        timezone_selector=select_timezone,
    )
    app.jinja_env.globals["get_locale"] = get_locale
    app.jinja_env.globals["get_timezone"] = get_timezone
