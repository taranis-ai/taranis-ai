from werkzeug.datastructures import ImmutableMultiDict


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
        tokens = _parse_key(full_key)
        _insert_value(result, tokens, val)
    return result


def _parse_key(key: str) -> list[str]:
    """
    Split a form-key string like "address[city]" or "items[]" into a list of tokens.
    """
    segments = key.split("[")
    tokens = [segments[0]]
    for seg in segments[1:]:
        if seg.endswith("]"):
            tokens.append(seg[:-1])
        else:
            tokens.append(seg)
    return tokens


def _insert_value(container, tokens: list[str], value: str):
    token = tokens[0]

    if isinstance(container, list):
        if token == "":
            if len(tokens) == 1:
                container.append(value)
            else:
                if not container or not isinstance(container[-1], dict):
                    container.append({})
                _insert_value(container[-1], tokens[1:], value)
        else:
            try:
                idx = int(token)
                while len(container) <= idx:
                    container.append({})
                if len(tokens) == 1:
                    container[idx] = value
                else:
                    if not isinstance(container[idx], dict):
                        container[idx] = {}
                    _insert_value(container[idx], tokens[1:], value)
            except ValueError:
                container.append({})
                _insert_value(container[-1], tokens, value)

    elif isinstance(container, dict):
        if token == "":
            return
        if len(tokens) == 1:
            container[token] = value
        else:
            next_token = tokens[1]
            if token not in container:
                container[token] = [] if next_token == "" else {}
            _insert_value(container[token], tokens[1:], value)
