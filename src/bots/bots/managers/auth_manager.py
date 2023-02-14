from functools import wraps
from flask import request
import ssl
from bots.config import settings


def initialize(app):
    if not settings.SSL_VERIFICATION:
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_key = request.headers.get("Authorization", "")
        api_key = settings.API_KEY

        if user_key != f"Bearer {api_key}":
            return {"error": "not authorized"}, 401
        return fn(*args, **kwargs)

    return wrapper
