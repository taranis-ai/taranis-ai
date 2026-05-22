from urllib.parse import parse_qs, urlparse

from flask import render_template, url_for
from lxml import html
from models.assess import AssessSource, FilterLists

from frontend.omnisearch import build_omnisearch_context, build_omnisearch_target_url, translate_assess_omnisearch


def _filter_lists() -> FilterLists:
    return FilterLists(
        tags=["apt", "ransomware"],
        sources=[AssessSource(id="source-1", name="Some Source"), AssessSource(id="source-2", name="Other Source")],
        groups=[{"id": "group-1", "name": "Some Group"}],
    )


def test_omnisearch_builds_scope_target_urls_and_ignores_unknown_colon_queries(app):
    with app.test_request_context("/frontend/search"):
        assert build_omnisearch_target_url("story: vpn").endswith("/assess?search=vpn")
        assert build_omnisearch_target_url("report: weekly").endswith("/analyze?search=weekly")
        assert build_omnisearch_target_url("product: executive").endswith("/publish?search=executive")
        assert build_omnisearch_target_url("cve:2026-1234") is None


def test_omnisearch_navbar_input_submits_to_global_search_and_loads_suggestions(app):
    with app.test_request_context("/"):
        markup = render_template("partials/omnisearch/omni_search.html")
        expected_suggestions = url_for("base.omnisearch_suggestions")

    tree = html.fromstring(markup)
    search_container = tree.xpath('//*[@role="search"]')[0]
    search_input = tree.xpath('//input[@id="omnisearch"]')[0]
    suggestions_panel = tree.xpath('//*[@id="omnisearch-suggestions"]')[0]

    assert "submitOmniSearch" in search_container.get("x-data")
    assert search_container.get("@click.outside") == "open = false"
    assert search_input.get("name") is None
    assert search_input.get("data-testid") == "omnisearch-input"
    assert search_input.get("@click") == "open = true"
    assert search_input.get("hx-get") == expected_suggestions
    assert search_input.get("hx-vals") == "js:{q: this.value}"
    assert search_input.get("hx-target") == "#omnisearch-suggestions"
    assert search_input.get("hx-trigger") == "focus, click, input changed delay:300ms, search"
    assert suggestions_panel.get("@click.outside") is None


def test_omnisearch_translates_issue_story_keywords():
    result = translate_assess_omnisearch("vpn tag:apt read:false sort:relevance", _filter_lists())

    assert result.errors == []
    assert result.params == {
        "search": ["vpn"],
        "tags": ["apt"],
        "read": ["false"],
        "sort": ["relevance"],
    }


def test_omnisearch_resolves_filter_list_values():
    result = translate_assess_omnisearch('source:"Some Source" group:"Some Group"', _filter_lists())

    assert result.errors == []
    assert result.params == {
        "source": ["source-1"],
        "group": ["group-1"],
    }


def test_omnisearch_treats_story_keywords_as_implicit_story_mode(app):
    with app.test_request_context("/frontend/search"):
        location = build_omnisearch_target_url("vpn cyber:yes in-report:false range:24h", _filter_lists())

    parsed_location = urlparse(location or "")
    assert parsed_location.path.endswith("/assess")
    assert parse_qs(parsed_location.query) == {
        "search": ["vpn"],
        "cybersecurity": ["yes"],
        "in_report": ["false"],
        "range": ["24h"],
    }


def test_omnisearch_translates_remaining_issue_keywords():
    result = translate_assess_omnisearch(
        "important:true relevant:false changed-by:me range:last7 from:2026-05-01T00:00 to:2026-05-22T12:30",
        _filter_lists(),
    )

    assert result.errors == []
    assert result.params == {
        "important": ["true"],
        "relevant": ["false"],
        "changed_by": ["me"],
        "range": ["last7"],
        "timefrom": ["2026-05-01T00:00"],
        "timeto": ["2026-05-22T12:30"],
    }


def test_omnisearch_reports_invalid_keyword_values():
    result = translate_assess_omnisearch("read:maybe", _filter_lists())

    assert result.params == {}
    assert result.errors == ["Invalid value 'maybe' for keyword 'read:'."]


def test_omnisearch_assess_filter_suggestions_are_story_only(app):
    with app.test_request_context("/frontend/search/suggestions?q=important:false"):
        context = build_omnisearch_context("important:false", filter_lists=_filter_lists())
        markup = render_template("partials/omnisearch/suggestions.html", search_context=context)

    tree = html.fromstring(markup)
    suggestion_text = tree.text_content()

    assert [link.scope for link in context.quick_links] == ["story"]
    assert context.buckets == []
    assert "Search stories" in suggestion_text
    assert "false important" not in suggestion_text
    assert "Search reports" not in suggestion_text
    assert "Search products" not in suggestion_text
    assert not tree.xpath('//*[@data-testid="omnisearch-scope-story"]')
    assert not tree.xpath('//*[@data-testid="omnisearch-scope-report"]')
    assert not tree.xpath('//*[@data-testid="omnisearch-scope-product"]')


def test_omnisearch_preserves_report_search_and_report_boolean_filter(app):
    with app.test_request_context("/frontend/search"):
        report_search = build_omnisearch_target_url("report: weekly incident", _filter_lists())
        report_filter = build_omnisearch_target_url("report:false", _filter_lists())

    assert report_search and report_search.endswith("/analyze?search=weekly+incident")
    parsed_filter = urlparse(report_filter or "")
    assert parsed_filter.path.endswith("/assess")
    assert parse_qs(parsed_filter.query) == {"in_report": ["false"]}
