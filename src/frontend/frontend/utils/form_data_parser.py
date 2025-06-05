def parse_key(key: str) -> list[str]:
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


def insert_value(container, tokens: list[str], value: str):
    token = tokens[0]

    if isinstance(container, list):
        if token == "":
            if len(tokens) == 1:
                container.append(value)
            else:
                next_token = tokens[1]
                if not container or not isinstance(container[-1], dict):
                    container.append({})
                insert_value(container[-1], tokens[1:], value)
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
                    insert_value(container[idx], tokens[1:], value)
            except ValueError:
                container.append({})
                insert_value(container[-1], tokens, value)

    elif isinstance(container, dict):
        if token == "":
            return
        if len(tokens) == 1:
            container[token] = value
        else:
            next_token = tokens[1]
            if token not in container:
                container[token] = [] if next_token == "" else {}
            insert_value(container[token], tokens[1:], value)
