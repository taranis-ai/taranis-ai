"""Flask adaptation of the shared, framework-independent operation contracts."""

import json
import re
from functools import partial, wraps

from flask import Flask, Response, current_app, g, jsonify, make_response, request
from models.api import ErrorResponse
from models.api_operations import find_operation
from models.base import TaranisBaseModel
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from core.log import logger


def current_operation():
    prefix = f"{current_app.config['APPLICATION_ROOT']}api"
    method = "GET" if request.method == "HEAD" else request.method
    route_path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", request.url_rule.rule) if request.url_rule else request.path
    if request.path.startswith(f"{prefix}/"):
        operation = find_operation(method, route_path.removeprefix(prefix))
        return operation if operation and operation.api_path else None
    path = "/" + route_path.removeprefix(current_app.config["APPLICATION_ROOT"])
    operation = find_operation(method, path)
    return operation if operation and not operation.api_path else None


def validate_request(handler=None, *, load_body=None):
    """Place inside authentication decorators so authorization still runs first."""

    if handler is None:
        return partial(validate_request, load_body=load_body)

    @wraps(handler)
    def validated(*args, **kwargs):
        operation = current_operation()
        if operation is None:
            raise RuntimeError("Request validator requires an operation contract")
        try:
            query = {key: request.args.getlist(key) if key in operation.repeated_query else request.args[key] for key in request.args}
            g.api_query = operation.query.model_validate(query)
            g.api_parameters = operation.parameters.model_validate(request.view_args or {})
            g.api_headers = operation.headers.model_validate(dict(request.headers))
            payload = None
            adapter = operation.body
            if load_body is not None:
                payload = load_body()
            elif request.mimetype == "multipart/form-data" and operation.uploads is not None:
                metadata = {
                    name: {"filename": file.filename, "content_type": file.content_type, "content_length": file.content_length}
                    for name, file in request.files.items()
                }
                g.api_uploads = operation.uploads.model_validate(metadata)
                if operation.file_body:
                    file = request.files["file"]
                    content = file.read()
                    file.seek(0)
                    if file.mimetype in operation.alternate_bodies:
                        adapter = operation.alternate_bodies[file.mimetype]
                        payload = content.decode("utf-8")
                    else:
                        payload = json.loads(content)
            elif request.get_data(cache=True):
                if request.mimetype not in operation.request_media_types:
                    raise ValueError("Unexpected request content type")
                if request.mimetype in operation.alternate_bodies:
                    adapter = operation.alternate_bodies[request.mimetype]
                    payload = request.get_data(as_text=True)
                else:
                    payload = request.get_json()
            context = {"filename": request.files["file"].filename} if "file" in request.files else {}
            g.api_body = adapter.validate_python(payload, context=context) if adapter is not None else operation.validate_body(payload)
            g.api_json = adapter.dump_python(g.api_body, mode="json", exclude_unset=True, exclude_none=False) if adapter else None
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"])
                if (
                    message := operation.field_error_messages.get(f"{location}:{error['type']}")
                    or operation.field_error_messages.get(location)
                    or operation.field_error_messages.get(".".join("*" if isinstance(part, int) else str(part) for part in error["loc"]))
                ):
                    return {"error": message}, 400
            if operation.validation_error_message is not None:
                return {"error": operation.validation_error_message}, 400
            if operation.validation_error_model is not None:
                return {"error": operation.validation_error_model.format_validation_errors(exc)}, 400
            return TaranisBaseModel.validation_error_response(exc, prefix=operation.invalid_request_message), 400
        except (ValueError, BadRequest, UnsupportedMediaType):
            return ErrorResponse(error=operation.invalid_request_message).model_dump(), 400
        try:
            return handler(*args, **kwargs)
        except ValidationError:
            if request.blueprint in {"config", "admin"}:
                raise
            logger.error(f"Invalid model produced by {request.method} {request.endpoint}")
            return ErrorResponse(error="Internal server error").model_dump(), 500

    validated.__dict__["api_request_validated"] = True
    return validated


def validate_response(response: Response) -> Response:
    operation = current_operation()
    if operation is None or request.method == "OPTIONS":
        return response
    try:
        contract = operation.response(response.status_code)
        if contract.body is None:
            contract.validate(None, content_type=response.content_type or "")
        elif contract.json_body is not None and response.is_json and not response.headers.get("Content-Disposition"):
            contract.json_body.validate_python(response.get_json())
        elif contract.download:
            if contract.body is None:
                raise ValueError("Download requires a metadata contract")
            contract.validate(
                {
                    "content_type": response.content_type,
                    "content_length": response.content_length,
                    "content_disposition": response.headers.get("Content-Disposition"),
                },
                content_type=response.content_type or "",
            )
        else:
            if response.is_streamed or response.direct_passthrough:
                raise ValueError("Unexpected streaming response")
            payload = response.get_json() if response.is_json else response.get_data()
            contract.validate(payload, content_type=response.content_type or "")
    except (ValidationError, ValueError, TypeError, BadRequest):
        logger.error(f"Invalid API response for {request.method} {request.endpoint} (status {response.status_code})")
        response.close()
        return make_response(jsonify(ErrorResponse(error="Internal server error").model_dump()), 500)
    return response


def initialize(app: Flask) -> None:
    app.after_request(validate_response)
