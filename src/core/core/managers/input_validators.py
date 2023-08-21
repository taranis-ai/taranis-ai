from functools import wraps
from flask import request, abort


def validate_id(id_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            id_value = kwargs.get(id_name, request.args.get(id_name, None))
            if id_value is None:
                abort(400, description=f"No {id_name} provided")
            try:
                id_value = int(id_value)
            except ValueError:
                abort(400, description=f"{id_name} must be an integer")
            if id_value < 0 or id_value > 2**31 - 1:
                abort(400, description=f"{id_name} must be a positive int32")
            return f(*args, **kwargs)

        return decorated_function

    return decorator
