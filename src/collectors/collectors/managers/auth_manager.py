import contextlib
from functools import wraps
from flask import request
import ssl
from collectors.config import Config


def initialize(app):
    if not Config.SSL_VERIFICATION:
        with contextlib.suppress(AttributeError):
            ssl._create_default_https_context = ssl._create_unverified_context


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_key = request.headers.get("Authorization", "")
        api_key = Config.API_KEY

        if user_key != f"Bearer {api_key}":
            return {"error": "not authorized"}, 401
        return fn(*args, **kwargs)

    return wrapper
