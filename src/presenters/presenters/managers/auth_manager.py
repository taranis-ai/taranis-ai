from functools import wraps
from flask import request
import ssl

api_key = ""


def initialize(app):
    global api_key
    api_key = app.config.get("API_KEY")
    if app.config.get("SSL_VERIFICATION") == "False":
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
        if user_key != f"Bearer {api_key}":
            return {"error": "not authorized"}, 401
        return fn(*args, **kwargs)

    return wrapper
