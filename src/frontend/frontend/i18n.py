from typing import Any

from flask import Flask, current_app, g, request
from flask_babel import Babel, get_locale, gettext
from flask_jwt_extended import current_user, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException


babel = Babel()


def _supported_locales() -> list[str]:
    return list(current_app.config.get("BABEL_SUPPORTED_LOCALES", ["en"]))


def _default_locale() -> str:
    return str(current_app.config.get("BABEL_DEFAULT_LOCALE", "en"))


def _profile_language(user: Any) -> str | None:
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    if isinstance(profile, dict):
        language = profile.get("language")
    else:
        language = getattr(profile, "language", None)
    if not isinstance(language, str):
        return None
    return language.strip().lower() or None


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


def select_locale() -> str:
    supported_locales = _supported_locales()
    default_locale = _default_locale()

    if not getattr(g, "skip_current_user_injection", False):
        try:
            verify_jwt_in_request(optional=True)
        except JWTExtendedException:
            pass
        else:
            if current_user:
                language = _profile_language(current_user)
                if language in supported_locales:
                    return language

    return _accepted_locale() or default_locale


def get_supported_language_options() -> list[dict[str, str]]:
    return [
        {"id": "en", "name": gettext("English")},
        {"id": "de", "name": gettext("German")},
    ]


def init(app: Flask) -> None:
    babel.init_app(app, locale_selector=select_locale)
    app.jinja_env.globals["get_locale"] = get_locale
