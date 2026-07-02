from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

from flask import url_for
from models.assess import FilterLists, Story
from models.base import TaranisBaseModel
from models.product import Product
from models.report import ReportItem
from werkzeug.exceptions import HTTPException

from frontend.cache_models import CacheObject, PagingData
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger


OmniSearchScope = Literal["story", "report", "product"]
AssessOmniSearchValueType = Literal["boolean", "changed_by", "cybersecurity", "datetime", "group", "range", "sort", "source", "tag"]


@dataclass(frozen=True)
class OmniSearchScopeDefinition:
    scope: OmniSearchScope
    command: str
    aliases: tuple[str, ...]
    label: str
    plural_label: str
    icon: str
    model: type[TaranisBaseModel]
    list_route: str
    detail_route: str
    detail_route_id: str


@dataclass(frozen=True)
class ParsedOmniSearchQuery:
    raw: str
    term: str
    scope: OmniSearchScope | None = None

    @property
    def has_query(self) -> bool:
        return bool(self.term)


@dataclass(frozen=True)
class OmniSearchResult:
    scope: OmniSearchScope
    label: str
    title: str
    description: str
    url: str


@dataclass(frozen=True)
class OmniSearchBucket:
    scope: OmniSearchScope
    label: str
    plural_label: str
    command: str
    icon: str
    search_url: str
    items: list[OmniSearchResult]
    total_count: int = 0
    error: str | None = None


@dataclass(frozen=True)
class OmniSearchQuickLink:
    scope: OmniSearchScope
    plural_label: str
    icon: str
    search_url: str


@dataclass(frozen=True)
class OmniSearchContext:
    parsed_query: ParsedOmniSearchQuery
    buckets: list[OmniSearchBucket]
    quick_links: list[OmniSearchQuickLink]
    scopes: tuple[OmniSearchScopeDefinition, ...]
    assess_suggestions: list[AssessOmniSearchSuggestion]
    errors: list[str]

    @property
    def has_results(self) -> bool:
        return any(bucket.items for bucket in self.buckets)


@dataclass(frozen=True)
class AssessOmniSearchKeyword:
    keyword: str
    aliases: tuple[str, ...]
    query_param: str
    value_type: AssessOmniSearchValueType
    repeatable: bool = False
    static_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssessOmniSearchToken:
    value: str
    keyword: str | None = None


@dataclass(frozen=True)
class AssessOmniSearchTranslation:
    params: dict[str, list[str]]
    errors: list[str]


@dataclass(frozen=True)
class ActiveAssessOmniSearchToken:
    raw: str
    start: int
    end: int
    mode: Literal["keyword", "value"]
    fragment: str
    keyword: str | None = None


@dataclass(frozen=True)
class AssessOmniSearchSuggestion:
    label: str
    detail: str
    replacement_query: str


@dataclass(frozen=True)
class AssessOmniSearchParseResult:
    tokens: list[AssessOmniSearchToken]
    errors: list[str]
    active_token: ActiveAssessOmniSearchToken
    known_keywords: list[str]


@dataclass(frozen=True)
class OmniSearchNavigation:
    url: str | None = None
    errors: list[str] | None = None


OMNISEARCH_SCOPES: tuple[OmniSearchScopeDefinition, ...] = (
    OmniSearchScopeDefinition(
        scope="story",
        command="story",
        aliases=("story", "stories", "assess"),
        label="Story",
        plural_label="Stories",
        icon="newspaper",
        model=Story,
        list_route="assess.assess",
        detail_route="assess.story",
        detail_route_id="story_id",
    ),
    OmniSearchScopeDefinition(
        scope="report",
        command="report",
        aliases=("report", "reports", "analyze", "analysis"),
        label="Report",
        plural_label="Reports",
        icon="presentation-chart-bar",
        model=ReportItem,
        list_route="analyze.analyze",
        detail_route="analyze.report",
        detail_route_id="report_id",
    ),
    OmniSearchScopeDefinition(
        scope="product",
        command="product",
        aliases=("product", "products", "publish"),
        label="Product",
        plural_label="Products",
        icon="paper-airplane",
        model=Product,
        list_route="publish.publish",
        detail_route="publish.product",
        detail_route_id="product_id",
    ),
)

OMNISEARCH_SCOPE_INDEX = {alias: scope for scope in OMNISEARCH_SCOPES for alias in scope.aliases}
BOOLEAN_VALUES = frozenset({"true", "false"})

ASSESS_OMNISEARCH_KEYWORDS: tuple[AssessOmniSearchKeyword, ...] = (
    AssessOmniSearchKeyword("source", ("source",), "source", "source", repeatable=True),
    AssessOmniSearchKeyword("group", ("group",), "group", "group", repeatable=True),
    AssessOmniSearchKeyword("tag", ("tag", "tags"), "tags", "tag", repeatable=True),
    AssessOmniSearchKeyword("read", ("read",), "read", "boolean", static_values=("true", "false")),
    AssessOmniSearchKeyword("important", ("important",), "important", "boolean", static_values=("true", "false")),
    AssessOmniSearchKeyword("relevant", ("relevant",), "relevant", "boolean", static_values=("true", "false")),
    AssessOmniSearchKeyword("in-report", ("in-report", "report"), "in_report", "boolean", static_values=("true", "false")),
    AssessOmniSearchKeyword(
        "cybersecurity",
        ("cybersecurity", "cyber"),
        "cybersecurity",
        "cybersecurity",
        static_values=("yes", "no", "mixed", "incomplete"),
    ),
    AssessOmniSearchKeyword("changed-by", ("changed-by",), "changed_by", "changed_by", static_values=("me",)),
    AssessOmniSearchKeyword("range", ("range",), "range", "range", static_values=("shift", "24h", "week", "day", "month", "last7")),
    AssessOmniSearchKeyword("from", ("from",), "timefrom", "datetime"),
    AssessOmniSearchKeyword("to", ("to",), "timeto", "datetime"),
    AssessOmniSearchKeyword(
        "sort",
        ("sort",),
        "sort",
        "sort",
        static_values=("date_desc", "date_asc", "relevance", "updated_desc", "updated_asc"),
    ),
)
ASSESS_OMNISEARCH_KEYWORD_INDEX = {alias.casefold(): keyword for keyword in ASSESS_OMNISEARCH_KEYWORDS for alias in keyword.aliases}


def parse_omnisearch_query(query: str) -> ParsedOmniSearchQuery:
    raw_query = query.strip()
    if not raw_query:
        return ParsedOmniSearchQuery(raw="", term="")

    prefix, separator, value = raw_query.partition(":")
    if separator:
        prefix_value = prefix.strip().casefold()
        scope = OMNISEARCH_SCOPE_INDEX.get(prefix_value)
        if scope:
            if scope.scope == "report" and _is_assess_report_filter(value):
                return ParsedOmniSearchQuery(raw=raw_query, term=raw_query)
            return ParsedOmniSearchQuery(raw=raw_query, term=value.strip(), scope=scope.scope)

    return ParsedOmniSearchQuery(raw=raw_query, term=raw_query)


def get_omnisearch_scope(scope: OmniSearchScope) -> OmniSearchScopeDefinition:
    return next(scope_definition for scope_definition in OMNISEARCH_SCOPES if scope_definition.scope == scope)


def build_omnisearch_search_url(scope: OmniSearchScope, term: str = "") -> str:
    scope_definition = get_omnisearch_scope(scope)
    if term:
        return url_for(scope_definition.list_route, search=term)
    return url_for(scope_definition.list_route)


def build_omnisearch_target_url(query: str, filter_lists: FilterLists | None = None) -> str | None:
    navigation = build_omnisearch_navigation(query, filter_lists or FilterLists(tags=[], sources=[], groups=[]))
    return navigation.url if not navigation.errors else None


def build_omnisearch_navigation(query: str, filter_lists: FilterLists) -> OmniSearchNavigation:
    parsed_query = parse_omnisearch_query(query)
    if parsed_query.scope in {"product", "report"}:
        return OmniSearchNavigation(url=build_omnisearch_search_url(parsed_query.scope, parsed_query.term), errors=[])

    if parsed_query.scope == "story":
        return _build_story_navigation(parsed_query.term, filter_lists)

    if is_assess_omnisearch_query(query):
        translation = translate_assess_omnisearch(query, filter_lists)
        return OmniSearchNavigation(url=_build_assess_url(translation.params), errors=translation.errors)

    return OmniSearchNavigation(errors=[])


def _build_story_navigation(query: str, filter_lists: FilterLists) -> OmniSearchNavigation:
    if is_assess_omnisearch_query(query):
        translation = translate_assess_omnisearch(query, filter_lists)
        return OmniSearchNavigation(url=_build_assess_url(translation.params), errors=translation.errors)
    return OmniSearchNavigation(url=build_omnisearch_search_url("story", query), errors=[])


def build_omnisearch_context(
    query: str,
    limit_per_scope: int = 4,
    filter_lists: FilterLists | None = None,
    errors: list[str] | None = None,
) -> OmniSearchContext:
    parsed_query = parse_omnisearch_query(query)
    filter_lists = filter_lists or FilterLists(tags=[], sources=[], groups=[])
    assess_query = _assess_feature_query(parsed_query, query)
    assess_suggestions = build_assess_omnisearch_suggestions(assess_query, filter_lists, limit=8) if assess_query is not None else []
    assess_filter_query = _is_assess_filter_query(parsed_query, query)
    quick_links = _build_quick_links(parsed_query, query, filter_lists, assess_filter_query)
    scope_definitions = _matching_scopes(parsed_query)
    buckets: list[OmniSearchBucket] = []
    if parsed_query.scope in {"report", "product"} or (
        not assess_filter_query and not _should_suppress_global_buckets(query, assess_suggestions)
    ):
        buckets = [_build_bucket(scope_definition, parsed_query.term, limit_per_scope) for scope_definition in scope_definitions]
    return OmniSearchContext(
        parsed_query=parsed_query,
        buckets=buckets,
        quick_links=quick_links,
        scopes=OMNISEARCH_SCOPES,
        assess_suggestions=assess_suggestions,
        errors=errors or [],
    )


def _matching_scopes(parsed_query: ParsedOmniSearchQuery) -> tuple[OmniSearchScopeDefinition, ...]:
    if parsed_query.scope:
        return (get_omnisearch_scope(parsed_query.scope),)
    return OMNISEARCH_SCOPES


def _assess_feature_query(parsed_query: ParsedOmniSearchQuery, query: str) -> str | None:
    if parsed_query.scope == "story":
        return parsed_query.term
    return query if parsed_query.scope is None else None


def _build_quick_links(
    parsed_query: ParsedOmniSearchQuery,
    query: str,
    filter_lists: FilterLists,
    assess_filter_query: bool,
) -> list[OmniSearchQuickLink]:
    if not parsed_query.raw or parsed_query.scope:
        return []
    if assess_filter_query:
        story_scope = get_omnisearch_scope("story")
        navigation = build_omnisearch_navigation(query, filter_lists)
        return [_quick_link_from_scope(story_scope, navigation.url or build_omnisearch_search_url("story", parsed_query.term))]
    return [
        _quick_link_from_scope(scope_definition, build_omnisearch_search_url(scope_definition.scope, parsed_query.term))
        for scope_definition in OMNISEARCH_SCOPES
    ]


def _quick_link_from_scope(scope_definition: OmniSearchScopeDefinition, search_url: str) -> OmniSearchQuickLink:
    return OmniSearchQuickLink(
        scope=scope_definition.scope,
        plural_label=scope_definition.plural_label,
        icon=scope_definition.icon,
        search_url=search_url,
    )


def _is_assess_filter_query(parsed_query: ParsedOmniSearchQuery, query: str) -> bool:
    if parsed_query.scope == "story":
        return is_assess_omnisearch_query(parsed_query.term)
    if parsed_query.scope is not None:
        return False
    return is_assess_omnisearch_query(query)


def is_assess_omnisearch_query(query: str) -> bool:
    return bool(parse_assess_omnisearch_full(query).known_keywords)


def needs_assess_filter_lists(query: str) -> bool:
    parsed_query = parse_omnisearch_query(query)
    assess_query = parsed_query.term if parsed_query.scope == "story" else query
    return _parse_result_needs_filter_lists(parse_assess_omnisearch_full(assess_query))


def parse_assess_omnisearch_full(query: str) -> AssessOmniSearchParseResult:
    raw_tokens, errors = _tokenize_raw(query)
    tokens: list[AssessOmniSearchToken] = []
    known_keywords: list[str] = []

    for raw_token in raw_tokens:
        token, known_keyword = _parse_assess_omnisearch_token(raw_token)
        if token:
            tokens.append(token)
        if known_keyword:
            known_keywords.append(known_keyword)

    return AssessOmniSearchParseResult(
        tokens=tokens,
        errors=errors,
        active_token=get_active_assess_omnisearch_token(query),
        known_keywords=known_keywords,
    )


def _parse_assess_omnisearch_token(raw_token: str) -> tuple[AssessOmniSearchToken | None, str | None]:
    colon_index = _find_unquoted_colon(raw_token)
    if colon_index > 0:
        keyword_text = _decode_token_text(raw_token[:colon_index]).strip().casefold()
        value = _decode_token_text(raw_token[colon_index + 1 :]).strip()
        if keyword_text in ASSESS_OMNISEARCH_KEYWORD_INDEX:
            return AssessOmniSearchToken(keyword=keyword_text, value=value), keyword_text

    value = _decode_token_text(raw_token).strip()
    if not value:
        return None, None
    return AssessOmniSearchToken(value=value), None


def translate_assess_omnisearch(query: str, filter_lists: FilterLists) -> AssessOmniSearchTranslation:
    parse_result = parse_assess_omnisearch_full(query)
    errors = list(parse_result.errors)
    params: dict[str, list[str]] = {}
    search_terms: list[str] = []

    for token in parse_result.tokens:
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

    return AssessOmniSearchTranslation(params=ordered_params, errors=errors)


def build_assess_omnisearch_suggestions(
    query: str,
    filter_lists: FilterLists,
    limit: int = 8,
) -> list[AssessOmniSearchSuggestion]:
    active_token = parse_assess_omnisearch_full(query).active_token
    if active_token.mode == "value" and active_token.keyword:
        keyword = ASSESS_OMNISEARCH_KEYWORD_INDEX[active_token.keyword]
        return _build_value_suggestions(query, active_token, keyword, filter_lists, limit)
    return _build_keyword_suggestions(query, active_token, limit)


def get_active_assess_omnisearch_token(query: str) -> ActiveAssessOmniSearchToken:
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
            return ActiveAssessOmniSearchToken(
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

    return ActiveAssessOmniSearchToken(
        raw=raw_token,
        start=token_start,
        end=len(query),
        mode="keyword",
        fragment=fragment,
    )


def _build_bucket(scope_definition: OmniSearchScopeDefinition, term: str, limit: int) -> OmniSearchBucket:
    if not term:
        return _empty_bucket(scope_definition, term)

    try:
        items = _search_scope(scope_definition, term, limit)
    except HTTPException as exc:
        logger.warning(f"Omnisearch scope {scope_definition.scope} unavailable: {exc}")
        return _empty_bucket(scope_definition, term, error="Unavailable")
    except Exception:
        logger.exception(f"Omnisearch scope {scope_definition.scope} failed")
        return _empty_bucket(scope_definition, term, error="Unavailable")

    return OmniSearchBucket(
        scope=scope_definition.scope,
        label=scope_definition.label,
        plural_label=scope_definition.plural_label,
        command=scope_definition.command,
        icon=scope_definition.icon,
        search_url=build_omnisearch_search_url(scope_definition.scope, term),
        items=[_result_from_model(scope_definition, item) for item in items.items],
        total_count=items.total_count,
    )


def _empty_bucket(scope_definition: OmniSearchScopeDefinition, term: str, error: str | None = None) -> OmniSearchBucket:
    return OmniSearchBucket(
        scope=scope_definition.scope,
        label=scope_definition.label,
        plural_label=scope_definition.plural_label,
        command=scope_definition.command,
        icon=scope_definition.icon,
        search_url=build_omnisearch_search_url(scope_definition.scope, term),
        items=[],
        error=error,
    )


def _search_scope(scope_definition: OmniSearchScopeDefinition, term: str, limit: int) -> CacheObject:
    paging_data = PagingData(
        page=1,
        limit=limit,
        search=term,
        query_params={
            "search": term,
            "limit": str(limit),
            "offset": "0",
        },
    )
    return DataPersistenceLayer().get_objects(scope_definition.model, paging_data)


def _result_from_model(scope_definition: OmniSearchScopeDefinition, item: TaranisBaseModel) -> OmniSearchResult:
    object_id = str(getattr(item, "id", "") or "")
    route_values: dict[str, Any] = {scope_definition.detail_route_id: object_id}
    return OmniSearchResult(
        scope=scope_definition.scope,
        label=scope_definition.label,
        title=_item_title(scope_definition.scope, item),
        description=_item_description(scope_definition.scope, item),
        url=url_for(scope_definition.detail_route, **route_values),
    )


def _item_title(scope: OmniSearchScope, item: TaranisBaseModel) -> str:
    if title := getattr(item, "title", None):
        return str(title)
    return f"{get_omnisearch_scope(scope).label} {getattr(item, 'id', '')}".strip()


def _item_description(scope: OmniSearchScope, item: TaranisBaseModel) -> str:
    if scope == "story":
        if summary := getattr(item, "summary", None):
            return str(summary)
        if description := getattr(item, "description", None):
            return str(description)
        news_items = getattr(item, "news_items", None) or []
        if news_items and (content := getattr(news_items[0], "content", None)):
            return str(content)
    if scope == "report":
        report_type = getattr(item, "report_item_type", None)
        completed = getattr(item, "completed", None)
        parts = [str(report_type)] if report_type else []
        if completed is not None:
            parts.append("completed" if completed else "incomplete")
        return " - ".join(parts)
    if scope == "product":
        if description := getattr(item, "description", None):
            return str(description)
    return ""


def quote_omnisearch_value(value: str) -> str:
    if not value:
        return '""'
    if re.search(r'\s|["\\]', value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _is_assess_report_filter(value: str) -> bool:
    return value.strip().casefold() in BOOLEAN_VALUES


def _build_assess_url(params: dict[str, list[str]]) -> str:
    assess_url = url_for("assess.assess")
    query_string = urlencode(params, doseq=True)
    return f"{assess_url}?{query_string}" if query_string else assess_url


def _should_suppress_global_buckets(query: str, assess_suggestions: list[AssessOmniSearchSuggestion]) -> bool:
    if not query.strip():
        return False
    active_token = get_active_assess_omnisearch_token(query)
    return active_token.mode == "value" or bool(assess_suggestions and active_token.fragment)


def _parse_result_needs_filter_lists(parse_result: AssessOmniSearchParseResult) -> bool:
    for token in parse_result.tokens:
        if token.keyword is None:
            continue
        keyword = ASSESS_OMNISEARCH_KEYWORD_INDEX[token.keyword]
        if keyword.value_type in {"source", "group"}:
            return True

    active_token = parse_result.active_token
    if active_token.mode == "value" and active_token.keyword:
        keyword = ASSESS_OMNISEARCH_KEYWORD_INDEX[active_token.keyword]
        return keyword.value_type in {"source", "group", "tag"}

    return False


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


def _normalize_keyword_value(keyword: AssessOmniSearchKeyword, value: str, filter_lists: FilterLists) -> tuple[str, str | None]:
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


def _normalize_static_value(keyword: AssessOmniSearchKeyword, value: str) -> tuple[str, str | None]:
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


def _build_keyword_suggestions(
    query: str,
    active_token: ActiveAssessOmniSearchToken,
    limit: int,
) -> list[AssessOmniSearchSuggestion]:
    fragment = active_token.fragment.casefold()
    suggestions: list[AssessOmniSearchSuggestion] = []

    for keyword in ASSESS_OMNISEARCH_KEYWORDS:
        matching_alias = next((alias for alias in keyword.aliases if not fragment or alias.startswith(fragment)), None)
        if not matching_alias:
            continue
        replacement_query = _replace_active_token(query, active_token, f"{matching_alias}:")
        suggestions.append(
            AssessOmniSearchSuggestion(
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
    active_token: ActiveAssessOmniSearchToken,
    keyword: AssessOmniSearchKeyword,
    filter_lists: FilterLists,
    limit: int,
) -> list[AssessOmniSearchSuggestion]:
    fragment = active_token.fragment.casefold()
    suggestions: list[AssessOmniSearchSuggestion] = []

    for label, value, detail in _iter_value_candidates(keyword, filter_lists):
        normalized_label = label.casefold()
        normalized_value = value.casefold()
        if fragment and fragment not in normalized_label and fragment not in normalized_value:
            continue
        if fragment and fragment in {normalized_label, normalized_value}:
            continue
        replacement = f"{keyword.keyword}:{quote_omnisearch_value(value)} "
        suggestions.append(
            AssessOmniSearchSuggestion(
                label=label,
                detail=detail,
                replacement_query=_replace_active_token(query, active_token, replacement),
            )
        )
        if len(suggestions) >= limit:
            break

    return suggestions


def _iter_value_candidates(keyword: AssessOmniSearchKeyword, filter_lists: FilterLists) -> list[tuple[str, str, str]]:
    match keyword.value_type:
        case "source":
            return [_filter_list_candidate(source) for source in filter_lists.sources]
        case "group":
            return [_filter_list_candidate(group) for group in filter_lists.groups]
        case "tag":
            return [(tag, tag, "tags") for tag in filter_lists.tags]
        case "boolean" | "changed_by" | "cybersecurity" | "range" | "sort":
            return [(value, value, keyword.query_param) for value in keyword.static_values]
        case "datetime":
            return []
    return []


def _filter_list_candidate(item: Any) -> tuple[str, str, str]:
    item_id = _get_filter_list_item_field(item, "id")
    value = _get_filter_list_item_field(item, "name") or item_id
    return value, value, item_id


def _replace_active_token(query: str, active_token: ActiveAssessOmniSearchToken, replacement: str) -> str:
    return f"{query[: active_token.start]}{replacement}{query[active_token.end :]}"
