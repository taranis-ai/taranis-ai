from typing import Any


def request_id_list(payload: dict[str, Any], singular_key: str, plural_key: str) -> list[str]:
    values: list[str] = []
    if singular := payload.get(singular_key):
        values.append(str(singular))
    if isinstance(plural := payload.get(plural_key), list):
        values.extend(str(item) for item in plural if item)
    elif plural:
        values.append(str(plural))
    return list(dict.fromkeys(values))
