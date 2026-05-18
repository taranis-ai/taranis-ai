from models.assess import AssessSource, FilterLists

from frontend.assess_omnisearch import build_assess_omnisearch_suggestions, translate_assess_omnisearch


def _filter_lists() -> FilterLists:
    return FilterLists(
        tags=["apt", "ransomware"],
        sources=[AssessSource(id="source-1", name="Some Source"), AssessSource(id="source-2", name="Other Source")],
        groups=[{"id": "group-1", "name": "Some Group"}],
    )


def test_omnisearch_translates_bare_terms_and_sidebar_filters():
    result = translate_assess_omnisearch("vpn tag:apt read:false sort:relevance", _filter_lists())

    assert result.errors == []
    assert result.params == {
        "search": ["vpn"],
        "tags": ["apt"],
        "read": ["false"],
        "sort": ["relevance"],
    }


def test_omnisearch_resolves_quoted_source_and_group_names():
    result = translate_assess_omnisearch('source:"Some Source" group:"Some Group"', _filter_lists())

    assert result.errors == []
    assert result.params == {
        "source": ["source-1"],
        "group": ["group-1"],
    }


def test_omnisearch_translates_aliases_and_static_values():
    result = translate_assess_omnisearch("cyber:yes in-report:false range:24h changed-by:me", _filter_lists())

    assert result.errors == []
    assert result.params == {
        "cybersecurity": ["yes"],
        "in_report": ["false"],
        "range": ["24h"],
        "changed_by": ["me"],
    }


def test_omnisearch_rejects_unknown_keywords_and_invalid_static_values():
    result = translate_assess_omnisearch("status:open read:maybe source:Missing", _filter_lists())

    assert result.params == {}
    assert result.errors == [
        "Unknown search keyword 'status'.",
        "Invalid value 'maybe' for keyword 'read:'.",
        "Unknown source 'Missing'.",
    ]


def test_omnisearch_preserves_quoted_bare_search_terms():
    result = translate_assess_omnisearch('"vpn access" malware', _filter_lists())

    assert result.errors == []
    assert result.params == {"search": ["vpn access malware"]}


def test_omnisearch_suggests_keywords_and_filter_values():
    keyword_suggestions = build_assess_omnisearch_suggestions("sou", _filter_lists())
    value_suggestions = build_assess_omnisearch_suggestions("source:Some", _filter_lists())

    assert keyword_suggestions[0].label == "source:"
    assert keyword_suggestions[0].replacement_query == "source:"
    assert value_suggestions[0].label == "Some Source"
    assert value_suggestions[0].detail == "source-1"
    assert value_suggestions[0].replacement_query == 'source:"Some Source" '
