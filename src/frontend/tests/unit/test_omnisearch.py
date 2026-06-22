from urllib.parse import parse_qs, urlparse

from flask import render_template, url_for
from lxml import html
from models.assess import AssessSource, FilterLists

from frontend import omnisearch
from frontend.omnisearch import (
    build_omnisearch_context,
    build_omnisearch_target_url,
    needs_assess_filter_lists,
    translate_assess_omnisearch,
)


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


def test_omnisearch_story_scope_preserves_plain_colon_search_terms(app):
    with app.test_request_context("/frontend/search"):
        location = build_omnisearch_target_url("story: http://example.com/cve:2026-1234", _filter_lists())

    parsed_location = urlparse(location or "")
    assert parsed_location.path.endswith("/assess")
    assert parse_qs(parsed_location.query) == {"search": ["http://example.com/cve:2026-1234"]}


def test_omnisearch_navbar_input_submits_to_global_search_and_loads_suggestions(app):
    with app.test_request_context("/"):
        markup = render_template("partials/omnisearch/omni_search.html")
        expected_suggestions = url_for("base.omnisearch_suggestions")

    tree = html.fromstring(markup)
    search_container = tree.xpath('//*[@role="search"]')[0]
    search_input = tree.xpath('//input[@id="omnisearch"]')[0]
    suggestions_panel = tree.xpath('//*[@id="omnisearch-suggestions"]')[0]

    assert search_container.get("x-data").startswith("omniSearch(")
    assert search_container.get("@click.outside") == "open = false"
    assert search_container.get("@keydown.window") == "focusShortcut($event)"
    assert search_container.get("@keydown.enter.prevent") is None
    assert search_input.get("name") is None
    assert search_input.get("data-testid") == "omnisearch-input"
    assert search_input.get("@click") == "open = true"
    assert search_input.get("@keydown.enter.prevent.stop") == "submitOmniSearch()"
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


def test_omnisearch_preserves_unknown_colon_tokens_as_search_terms():
    result = translate_assess_omnisearch("read:false cve:2026-1234 http://example.com", _filter_lists())

    assert result.errors == []
    assert result.params == {
        "search": ["cve:2026-1234 http://example.com"],
        "read": ["false"],
    }


def test_omnisearch_loads_filter_lists_only_when_value_suggestions_or_resolution_need_them():
    assert needs_assess_filter_lists("") is False
    assert needs_assess_filter_lists("sou") is False
    assert needs_assess_filter_lists("read:false") is False
    assert needs_assess_filter_lists("story: read:false") is False
    assert needs_assess_filter_lists("source:") is True
    assert needs_assess_filter_lists("group:Some") is True
    assert needs_assess_filter_lists("tag:ap") is True
    assert needs_assess_filter_lists("story: source:Some") is True


def test_omnisearch_scope_search_uses_first_page_offset(app, monkeypatch):
    captured = {}

    class FakePersistenceLayer:
        def get_objects(self, model, paging_data):
            captured["model"] = model
            captured["paging_data"] = paging_data
            return omnisearch.CacheObject([])

    monkeypatch.setattr(omnisearch, "DataPersistenceLayer", FakePersistenceLayer)

    with app.test_request_context("/frontend/search/suggestions?q=report:foo"):
        context = build_omnisearch_context("report:foo", limit_per_scope=4)

    assert [bucket.scope for bucket in context.buckets] == ["report"]
    assert captured["paging_data"].page == 1
    assert captured["paging_data"].query_params == {"search": "foo", "limit": "4", "offset": "0"}


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


def test_omnisearch_explicit_non_story_scopes_do_not_show_assess_suggestions(app):
    with app.test_request_context("/frontend/search/suggestions?q=report:"):
        report_context = build_omnisearch_context("report:", filter_lists=_filter_lists())
        report_markup = render_template("partials/omnisearch/suggestions.html", search_context=report_context)

    with app.test_request_context("/frontend/search/suggestions?q=product:"):
        product_context = build_omnisearch_context("product:", filter_lists=_filter_lists())
        product_markup = render_template("partials/omnisearch/suggestions.html", search_context=product_context)

    assert report_context.assess_suggestions == []
    assert product_context.assess_suggestions == []
    assert [bucket.scope for bucket in report_context.buckets] == ["report"]
    assert [bucket.scope for bucket in product_context.buckets] == ["product"]
    assert "tag:" not in html.fromstring(report_markup).text_content()
    assert "read:" not in html.fromstring(report_markup).text_content()
    assert "tag:" not in html.fromstring(product_markup).text_content()
    assert "read:" not in html.fromstring(product_markup).text_content()


def test_omnisearch_suggestions_surface_validation_errors(authenticated_client):
    with authenticated_client.application.test_request_context("/"):
        suggestions_url = url_for("base.omnisearch_suggestions", q="read:maybe")

    response = authenticated_client.get(suggestions_url, headers={"HX-Request": "true"})
    tree = html.fromstring(response.text)

    assert response.status_code == 200
    assert tree.xpath('//*[@data-testid="omnisearch-errors"]/div/text()') == ["Invalid value 'maybe' for keyword 'read:'."]


def test_omnisearch_preserves_report_search_and_report_boolean_filter(app):
    with app.test_request_context("/frontend/search"):
        report_search = build_omnisearch_target_url("report: weekly incident", _filter_lists())
        report_filter = build_omnisearch_target_url("report:false", _filter_lists())

    assert report_search and report_search.endswith("/analyze?search=weekly+incident")
    parsed_filter = urlparse(report_filter or "")
    assert parsed_filter.path.endswith("/assess")
    assert parse_qs(parsed_filter.query) == {"in_report": ["false"]}
