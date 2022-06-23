from functools import wraps
from flask import request
import os
import ssl

api_key = os.getenv('API_KEY')

if os.getenv('SSL_VERIFICATION') == "False":
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'Authorization' not in request.headers or request.headers['Authorization'] != f'Bearer {api_key}':
            return {'error': 'not authorized'}, 401
        return fn(*args, **kwargs)

    return wrapper
