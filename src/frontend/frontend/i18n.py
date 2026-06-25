from functools import cache
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from flask import Flask, g, request
from flask_babel import Babel, gettext
from flask_jwt_extended import current_user, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException

from frontend.config import Config


babel = Babel()


def _profile_value(user: Any, key: str) -> str | None:
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    if isinstance(profile, dict):
        value = profile.get(key)
    else:
        value = getattr(profile, key, None)
    return value.strip() or None if isinstance(value, str) else None


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
    for locale, _quality in request.accept_languages:
        normalized_locale = locale.lower()
        if normalized_locale in Config.BABEL_SUPPORTED_LOCALES:
            return normalized_locale
        primary_locale = normalized_locale.split("-", 1)[0]
        if primary_locale in Config.BABEL_SUPPORTED_LOCALES:
            return primary_locale

    return None


def select_locale() -> str:
    if not getattr(g, "skip_current_user_injection", False):
        try:
            verify_jwt_in_request(optional=True)
        except JWTExtendedException:
            pass
        else:
            if current_user:
                language = _profile_language(current_user)
                if language is not None and language in Config.BABEL_SUPPORTED_LOCALES:
                    return language

    return _accepted_locale() or Config.BABEL_DEFAULT_LOCALE


def select_timezone() -> str:
    if not getattr(g, "skip_current_user_injection", False):
        try:
            verify_jwt_in_request(optional=True)
        except JWTExtendedException:
            pass
        else:
            if current_user:
                if timezone_name := _valid_timezone(_profile_value(current_user, "timezone")):
                    return timezone_name

    return Config.BABEL_DEFAULT_TIMEZONE


def get_supported_language_options() -> list[dict[str, str]]:
    names = {
        "en": gettext("English"),
        "de": gettext("German"),
    }
    return [{"id": locale, "name": names.get(locale, locale)} for locale in Config.BABEL_SUPPORTED_LOCALES]


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
