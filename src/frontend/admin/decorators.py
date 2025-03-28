from functools import wraps
from flask import request


def validate_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return {"error": "Missing JSON in request"}, 400

        return f(*args, **kwargs)

    return decorated_function


def extract_args(*keys):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            filter_args = {k: request.args[k] for k in keys if k in request.args}
            kwargs["filter_args"] = filter_args
            return f(*args, **kwargs)

        return decorated_function

    return decorator
