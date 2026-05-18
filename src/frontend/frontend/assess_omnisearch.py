from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from models.assess import FilterLists


OmniSearchValueType = Literal["boolean", "changed_by", "cybersecurity", "datetime", "group", "range", "sort", "source", "tag"]


@dataclass(frozen=True)
class OmniSearchKeyword:
    keyword: str
    aliases: tuple[str, ...]
    query_param: str
    value_type: OmniSearchValueType
    repeatable: bool = False
    static_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class OmniSearchToken:
    value: str
    keyword: str | None = None


@dataclass(frozen=True)
class OmniSearchTranslation:
    params: dict[str, list[str]]
    errors: list[str]


@dataclass(frozen=True)
class ActiveOmniSearchToken:
    raw: str
    start: int
    end: int
    mode: Literal["keyword", "value"]
    fragment: str
    keyword: str | None = None


@dataclass(frozen=True)
class OmniSearchSuggestion:
    label: str
    detail: str
    replacement_query: str


ASSESS_OMNISEARCH_KEYWORDS: tuple[OmniSearchKeyword, ...] = (
    OmniSearchKeyword("source", ("source",), "source", "source", repeatable=True),
    OmniSearchKeyword("group", ("group",), "group", "group", repeatable=True),
    OmniSearchKeyword("tag", ("tag", "tags"), "tags", "tag", repeatable=True),
    OmniSearchKeyword("read", ("read",), "read", "boolean", static_values=("true", "false")),
    OmniSearchKeyword("important", ("important",), "important", "boolean", static_values=("true", "false")),
    OmniSearchKeyword("relevant", ("relevant",), "relevant", "boolean", static_values=("true", "false")),
    OmniSearchKeyword("in-report", ("in-report", "report"), "in_report", "boolean", static_values=("true", "false")),
    OmniSearchKeyword(
        "cybersecurity",
        ("cybersecurity", "cyber"),
        "cybersecurity",
        "cybersecurity",
        static_values=("yes", "no", "mixed", "incomplete"),
    ),
    OmniSearchKeyword("changed-by", ("changed-by",), "changed_by", "changed_by", static_values=("me",)),
    OmniSearchKeyword("range", ("range",), "range", "range", static_values=("shift", "24h", "week", "day", "month")),
    OmniSearchKeyword("from", ("from",), "timefrom", "datetime"),
    OmniSearchKeyword("to", ("to",), "timeto", "datetime"),
    OmniSearchKeyword(
        "sort",
        ("sort",),
        "sort",
        "sort",
        static_values=("date_desc", "date_asc", "relevance", "updated_desc", "updated_asc"),
    ),
)

ASSESS_OMNISEARCH_KEYWORD_INDEX = {alias.casefold(): keyword for keyword in ASSESS_OMNISEARCH_KEYWORDS for alias in keyword.aliases}


def parse_assess_omnisearch(query: str) -> tuple[list[OmniSearchToken], list[str]]:
    raw_tokens, errors = _tokenize_raw(query)
    tokens: list[OmniSearchToken] = []

    for raw_token in raw_tokens:
        colon_index = _find_unquoted_colon(raw_token)
        if colon_index > 0:
            keyword_text = _decode_token_text(raw_token[:colon_index]).strip().casefold()
            value = _decode_token_text(raw_token[colon_index + 1 :]).strip()
            if keyword_text in ASSESS_OMNISEARCH_KEYWORD_INDEX:
                tokens.append(OmniSearchToken(keyword=keyword_text, value=value))
            else:
                errors.append(f"Unknown search keyword '{keyword_text}'.")
            continue

        value = _decode_token_text(raw_token).strip()
        if value:
            tokens.append(OmniSearchToken(value=value))

    return tokens, errors


def translate_assess_omnisearch(query: str, filter_lists: FilterLists) -> OmniSearchTranslation:
    tokens, errors = parse_assess_omnisearch(query)
    params: dict[str, list[str]] = {}
    search_terms: list[str] = []

    for token in tokens:
        if token.keyword is None:
            search_terms.append(token.value)
            continue

        keyword = ASSESS_OMNISEARCH_KEYWORD_INDEX[token.keyword]
        if not token.value:
            errors.append(f"Keyword '{keyword.keyword}:' requires a value.")
            continue

        if not keyword.repeatable and keyword.query_param in params:
            errors.append(f"Keyword '{keyword.keyword}:' can only be used once.")
            continue

        normalized_value, error = _normalize_keyword_value(keyword, token.value, filter_lists)
        if error:
            errors.append(error)
            continue

        params.setdefault(keyword.query_param, []).append(normalized_value)

    ordered_params: dict[str, list[str]] = {}
    if search_terms:
        ordered_params["search"] = [" ".join(search_terms)]
    ordered_params.update(params)

    return OmniSearchTranslation(params=ordered_params, errors=errors)


def build_assess_omnisearch_suggestions(
    query: str,
    filter_lists: FilterLists,
    limit: int = 8,
) -> list[OmniSearchSuggestion]:
    active_token = get_active_omnisearch_token(query)
    if active_token.mode == "value" and active_token.keyword:
        keyword = ASSESS_OMNISEARCH_KEYWORD_INDEX[active_token.keyword]
        return _build_value_suggestions(query, active_token, keyword, filter_lists, limit)
    return _build_keyword_suggestions(query, active_token, limit)


def get_active_omnisearch_token(query: str) -> ActiveOmniSearchToken:
    token_start = 0
    in_quote = False
    escaped = False

    for index, char in enumerate(query):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char.isspace() and not in_quote:
            token_start = index + 1

    raw_token = query[token_start:]
    colon_index = _find_unquoted_colon(raw_token)
    if colon_index > 0:
        keyword_text = _decode_token_text(raw_token[:colon_index]).strip().casefold()
        if keyword_text in ASSESS_OMNISEARCH_KEYWORD_INDEX:
            return ActiveOmniSearchToken(
                raw=raw_token,
                start=token_start,
                end=len(query),
                mode="value",
                fragment=_decode_token_text(raw_token[colon_index + 1 :]).strip(),
                keyword=keyword_text,
            )
        fragment = _decode_token_text(raw_token[:colon_index]).strip()
    else:
        fragment = _decode_token_text(raw_token).strip()

    return ActiveOmniSearchToken(
        raw=raw_token,
        start=token_start,
        end=len(query),
        mode="keyword",
        fragment=fragment,
    )


def quote_omnisearch_value(value: str) -> str:
    if not value:
        return '""'
    if re.search(r'\s|["\\]', value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _tokenize_raw(query: str) -> tuple[list[str], list[str]]:
    tokens: list[str] = []
    errors: list[str] = []
    token_start: int | None = None
    in_quote = False
    escaped = False

    for index, char in enumerate(query):
        if token_start is None and not char.isspace():
            token_start = index

        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char.isspace() and not in_quote and token_start is not None:
            if token_start < index:
                tokens.append(query[token_start:index])
            token_start = None

    if token_start is not None:
        tokens.append(query[token_start:])
    if in_quote:
        errors.append("Unclosed quote in search query.")

    return tokens, errors


def _decode_token_text(raw_token: str) -> str:
    chars: list[str] = []
    escaped = False

    for char in raw_token:
        if escaped:
            chars.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            continue
        chars.append(char)

    if escaped:
        chars.append("\\")

    return "".join(chars)


def _find_unquoted_colon(raw_token: str) -> int:
    in_quote = False
    escaped = False

    for index, char in enumerate(raw_token):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == ":" and not in_quote:
            return index

    return -1


def _normalize_keyword_value(keyword: OmniSearchKeyword, value: str, filter_lists: FilterLists) -> tuple[str, str | None]:
    match keyword.value_type:
        case "source":
            return _resolve_filter_list_object(value, filter_lists.sources, "source")
        case "group":
            return _resolve_filter_list_object(value, filter_lists.groups, "group")
        case "tag":
            return value, None
        case "boolean" | "changed_by" | "cybersecurity" | "sort":
            return _normalize_static_value(keyword, value)
        case "range":
            lowered_value = value.casefold()
            if lowered_value in keyword.static_values or re.fullmatch(r"last[1-9]\d*", lowered_value):
                return lowered_value, None
            return "", f"Invalid value '{value}' for keyword '{keyword.keyword}:'."
        case "datetime":
            return value, None
    return value, None


def _normalize_static_value(keyword: OmniSearchKeyword, value: str) -> tuple[str, str | None]:
    lowered_value = value.casefold()
    if lowered_value in keyword.static_values:
        return lowered_value, None
    return "", f"Invalid value '{value}' for keyword '{keyword.keyword}:'."


def _resolve_filter_list_object(value: str, items: list[Any], item_type: str) -> tuple[str, str | None]:
    normalized_value = value.casefold()
    for item in items:
        item_id = _get_filter_list_item_field(item, "id")
        item_name = _get_filter_list_item_field(item, "name")
        if normalized_value in {item_id.casefold(), item_name.casefold()} and item_id:
            return item_id, None
    return "", f"Unknown {item_type} '{value}'."


def _get_filter_list_item_field(item: Any, field_name: str) -> str:
    if isinstance(item, dict):
        return str(item.get(field_name) or "")
    return str(getattr(item, field_name, "") or "")


def _build_keyword_suggestions(query: str, active_token: ActiveOmniSearchToken, limit: int) -> list[OmniSearchSuggestion]:
    fragment = active_token.fragment.casefold()
    suggestions: list[OmniSearchSuggestion] = []

    for keyword in ASSESS_OMNISEARCH_KEYWORDS:
        matching_alias = next((alias for alias in keyword.aliases if not fragment or alias.startswith(fragment)), None)
        if not matching_alias:
            continue
        replacement_query = _replace_active_token(query, active_token, f"{matching_alias}:")
        suggestions.append(
            OmniSearchSuggestion(
                label=f"{matching_alias}:",
                detail=keyword.query_param,
                replacement_query=replacement_query,
            )
        )
        if len(suggestions) >= limit:
            break

    return suggestions


def _build_value_suggestions(
    query: str,
    active_token: ActiveOmniSearchToken,
    keyword: OmniSearchKeyword,
    filter_lists: FilterLists,
    limit: int,
) -> list[OmniSearchSuggestion]:
    fragment = active_token.fragment.casefold()
    suggestions: list[OmniSearchSuggestion] = []

    for label, value, detail in _iter_value_candidates(keyword, filter_lists):
        if fragment and fragment not in label.casefold() and fragment not in value.casefold():
            continue
        replacement = f"{keyword.keyword}:{quote_omnisearch_value(value)} "
        suggestions.append(
            OmniSearchSuggestion(
                label=label,
                detail=detail,
                replacement_query=_replace_active_token(query, active_token, replacement),
            )
        )
        if len(suggestions) >= limit:
            break

    return suggestions


def _iter_value_candidates(keyword: OmniSearchKeyword, filter_lists: FilterLists) -> list[tuple[str, str, str]]:
    match keyword.value_type:
        case "source":
            return [
                (
                    _get_filter_list_item_field(source, "name") or _get_filter_list_item_field(source, "id"),
                    _get_filter_list_item_field(source, "name") or _get_filter_list_item_field(source, "id"),
                    _get_filter_list_item_field(source, "id"),
                )
                for source in filter_lists.sources
            ]
        case "group":
            return [
                (
                    _get_filter_list_item_field(group, "name") or _get_filter_list_item_field(group, "id"),
                    _get_filter_list_item_field(group, "name") or _get_filter_list_item_field(group, "id"),
                    _get_filter_list_item_field(group, "id"),
                )
                for group in filter_lists.groups
            ]
        case "tag":
            return [(tag, tag, "tags") for tag in filter_lists.tags]
        case "boolean" | "changed_by" | "cybersecurity" | "range" | "sort":
            return [(value, value, keyword.query_param) for value in keyword.static_values]
        case "datetime":
            return []
    return []


def _replace_active_token(query: str, active_token: ActiveOmniSearchToken, replacement: str) -> str:
    return f"{query[: active_token.start]}{replacement}{query[active_token.end :]}"
