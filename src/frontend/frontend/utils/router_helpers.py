from flask import request
from werkzeug.datastructures import MultiDict
from typing import Type, get_origin, Union, get_args
from pydantic import BaseModel


def is_htmx_request() -> bool:
    return "HX-Request" in request.headers


def convert_query_params(query_params: MultiDict[str, str], model: Type[BaseModel]) -> dict:
    """
    group query parameters into lists if model defines them

    :param query_params: flasks request.args
    :param model: query parameter's model
    :return: resulting parameters
    """
    return {
        **query_params.to_dict(),
        **{
            key: value
            for key, value in query_params.to_dict(flat=False).items()
            if key in model.model_fields and _is_list(model.model_fields[key].annotation)  # type: ignore
        },
    }


def _is_list(type_: Type) -> bool:
    origin = get_origin(type_)
    if origin is list:
        return True
    if origin is Union:
        return any(_is_list(t) for t in get_args(type_))
    return False
