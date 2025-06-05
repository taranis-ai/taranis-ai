from flask import request
from werkzeug.datastructures import ImmutableMultiDict, MultiDict
from typing import Type, get_origin, Union, get_args
from pydantic import BaseModel

from frontend.utils.form_data_parser import parse_key, insert_value


def is_htmx_request() -> bool:
    return "HX-Request" in request.headers


def parse_formdata(formdata: ImmutableMultiDict) -> dict:
    """
    Convert a Werkzeug ImmutableMultiDict of form fields into a nested
    structure of dicts and lists, following PHP-style bracket notation.

    Examples tested:
      1) Simple keys:
         { "name": "John", "age": "30" }
      2) One level of nesting:
         { "address[city]": "New York" } → { "address": { "city": "New York" } }
      3) Lists:
         { "items[]": "item1",
           "items[]": "item2" }
         →
         { "items": ["item1", "item2"] }
      4) Dict-of-dicts via numeric indices:
         { "details[0][key]": "value1",
           "details[0][value]": "value2",
           "details[1][key]": "value3",
           "details[1][value]": "value4" }
         →
         { "details": {
             "0": { "key": "value1", "value": "value2" },
             "1": { "key": "value3", "value": "value4" }
           }
         }
      5) List of dicts without explicit index:
         { "attribute_groups[][index]": "0",
           "attribute_groups[][title]": "XXX",
           "attribute_groups[][description]": "uiae" }
         →
         { "attribute_groups": [
             { "index": "0", "title": "XXX", "description": "uiae" }
           ]
         }
    """
    result = {}
    # Each key may appear multiple times; getlist(key) preserves insertion order
    for full_key, val in formdata.items(multi=True):
        tokens = parse_key(full_key)
        insert_value(result, tokens, val)
    return result


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
