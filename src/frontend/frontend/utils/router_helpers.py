from typing import Any, Union, get_args, get_origin

from flask import request
from pydantic import BaseModel
from werkzeug.datastructures import MultiDict

from frontend.cache_models import PagingData


def is_htmx_request() -> bool:
    return "HX-Request" in request.headers


def convert_query_params(query_params: MultiDict[str, str], model: type[BaseModel]) -> dict[str, Any]:
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


def parse_paging_data(params: dict[str, list[str]] | None = None) -> PagingData:
    """Unmarshal query parameters into a PagingData model."""
    source_params = params if params is not None else request.args.to_dict(flat=False)
    args: dict[str, list[str]] = {key: list(value) for key, value in source_params.items()}

    # Flatten single-value entries for convenience in query_params
    query_params: dict[str, str | list[str]] = {k: v[0] if len(v) == 1 else v for k, v in args.items()}

    page = request.args.get("page", type=int)
    limit = request.args.get("limit", type=int)
    order = request.args.get("order")
    search = request.args.get("search")

    return PagingData(
        page=page,
        limit=limit,
        order=order,
        search=search,
        query_params=query_params,
    )


def _is_list(type_: type) -> bool:
    origin = get_origin(type_)
    if origin is list:
        return True
    if origin is Union:
        return any(_is_list(t) for t in get_args(type_))
    return False
