from typing import Any

from werkzeug.datastructures import ImmutableMultiDict


def parse_formdata(formdata: ImmutableMultiDict[Any, Any]) -> dict[str, Any]:
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
    result: dict[str, Any] = {}
    list_counters: dict[int, dict[tuple[str, ...], int]] = {}
    # Each key may appear multiple times; getlist(key) preserves insertion order
    for full_key, val in formdata.items(multi=True):
        tokens = _parse_key(full_key)
        _insert_value(result, tokens, val, list_counters)
    return result


def _parse_key(key: str) -> list[str]:
    """
    Split a form-key string like "address[city]" or "items[]" into a list of tokens.
    """
    segments = key.split("[")
    tokens = [segments[0]]
    for seg in segments[1:]:
        tokens.append(seg[:-1] if seg.endswith("]") else seg)
    return tokens


def _expected_container_type(tokens: list[str]) -> str:
    """
    Decide what container type (list or dict) is needed to satisfy the remaining tokens.
    """
    if not tokens:
        return "dict"
    return "list" if tokens[0] == "" else "dict"


def _make_container(tokens: list[str]) -> list[Any] | dict[str, Any]:
    """
    Create a new container (dict or list) suitable for the upcoming tokens.
    """
    return [] if _expected_container_type(tokens) == "list" else {}


def _get_list_target(
    container: list[Any],
    remaining_tokens: list[str],
    list_counters: dict[int, dict[tuple[str, ...], int]],
) -> Any:
    """
    Determine which element of the list should receive the value corresponding to remaining_tokens.
    Values with the same trailing token sequence are distributed by occurrence index so that
    repeated keys without explicit numeric indices stay aligned regardless of iteration order.
    """
    counters = list_counters.setdefault(id(container), {})
    key = tuple(remaining_tokens)
    idx = counters.get(key, 0)
    counters[key] = idx + 1

    expected_type = _expected_container_type(remaining_tokens)

    while len(container) <= idx:
        container.append(_make_container(remaining_tokens))

    target = container[idx]

    if expected_type == "dict" and not isinstance(target, dict):
        target = {}
        container[idx] = target
    elif expected_type == "list" and not isinstance(target, list):
        target = []
        container[idx] = target

    return target


def _insert_value(
    container: list[Any] | dict[str, Any],
    tokens: list[str],
    value: Any,
    list_counters: dict[int, dict[tuple[str, ...], int]],
) -> None:
    token = tokens[0]

    if isinstance(container, list):
        if token == "":
            if len(tokens) == 1:
                container.append(value)
            else:
                remaining_tokens = tokens[1:]
                target = _get_list_target(container, remaining_tokens, list_counters)
                _insert_value(target, remaining_tokens, value, list_counters)
        else:
            try:
                idx = int(token)
            except ValueError:
                container.append({})
                _insert_value(container[-1], tokens, value, list_counters)
                return

            while len(container) <= idx:
                container.append({})

            if len(tokens) == 1:
                container[idx] = value
            else:
                if not isinstance(container[idx], dict):
                    container[idx] = {}
                _insert_value(container[idx], tokens[1:], value, list_counters)

    elif isinstance(container, dict):
        if token == "":
            return

        if len(tokens) == 1:
            container[token] = value
        else:
            next_token = tokens[1]
            if token not in container:
                container[token] = [] if next_token == "" else {}
            _insert_value(container[token], tokens[1:], value, list_counters)
