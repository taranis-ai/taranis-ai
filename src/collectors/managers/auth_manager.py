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

        if not request.headers.has_key('Authorization') or request.headers['Authorization'] != ('Bearer ' + api_key):
            return {'error': 'not authorized'}, 401
        else:
            return fn(*args, **kwargs)

    return wrapper
