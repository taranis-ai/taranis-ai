"""Flask boundaries for the frontend's structured data endpoints."""

import re
from functools import wraps

from flask import current_app, g, make_response, request
from models.frontend_api import OPERATIONS
from pydantic import ValidationError

from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata


def operation():
    if request.url_rule is None:
        return None
    path = "/" + request.url_rule.rule.removeprefix(current_app.config["APPLICATION_ROOT"])
    path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
    return next((op for op in OPERATIONS if op.match("GET" if request.method == "HEAD" else request.method, path) is not None), None)


def validate_request(*, load_body=None):
    def decorate(handler):
        @wraps(handler)
        def validated(*args, **kwargs):
            contract = operation()
            if contract is None:
                raise RuntimeError("Missing frontend API contract")
            try:
                contract.parameters.model_validate(request.view_args or {})
                contract.query.model_validate(request.args.to_dict())
                contract.headers.model_validate(dict(request.headers))
                if load_body is not None:
                    payload = load_body()
                elif request.is_json:
                    payload = request.get_json(silent=True)
                else:
                    payload = parse_formdata(request.form)
                if contract.body is not None:
                    payload = payload or {}
                    g.frontend_api_json = contract.body.dump_python(contract.body.validate_python(payload), mode="json", exclude_unset=True)
                else:
                    contract.validate_body(payload or None)
            except ValidationError, ValueError, TypeError, AttributeError:
                return "Invalid request payload", 400
            return handler(*args, **kwargs)

        validated.__dict__["api_request_validated"] = True
        return validated

    return decorate


def validate_response(response):
    contract = operation()
    if contract is None:
        return response
    try:
        response_contract = contract.response(response.status_code)
        payload = (
            {
                "content_type": response.content_type,
                "content_length": response.content_length,
                "content_disposition": response.headers.get("Content-Disposition"),
            }
            if response_contract.download
            else response.get_json()
        )
        response_contract.validate(payload, content_type=response.content_type or "")
    except ValidationError, ValueError:
        logger.error(f"Invalid frontend API output from {request.endpoint}")
        response.close()
        return make_response("Internal server error", 500)
    return response
