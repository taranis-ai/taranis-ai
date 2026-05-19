from typing import Any

from flask import Response, jsonify


def public_validation_error(error: Exception, default: str) -> str:
    message = str(error)
    if message == "Icon payload is not a valid image file.":
        return "Icon payload is not a valid image file."
    if message == "Invalid presenter template path":
        return "Invalid presenter template path"
    return default


def jsonify_result(payload: Any, status: int | None = None):
    if status is not None:
        if isinstance(payload, Response):
            payload.status_code = status
            return payload
        return jsonify(payload), status

    if isinstance(payload, Response):
        return payload

    if isinstance(payload, tuple) and len(payload) == 2 and isinstance(payload[1], int):
        response_payload, response_status = payload
        if isinstance(response_payload, Response):
            response_payload.status_code = response_status
            return response_payload
        return jsonify(response_payload), response_status

    return jsonify(payload)
