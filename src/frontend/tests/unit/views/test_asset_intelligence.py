from urllib.parse import parse_qs, urlparse

import pytest
from lxml import html
from models.asset_intelligence import IntelligenceFilters

from frontend.cache import add_user_to_cache
from frontend.config import Config


@pytest.mark.parametrize("route", ["/assets/intelligence", "/assets/host-1/intelligence"])
@pytest.mark.parametrize(
    ("local_day", "utc_start", "utc_end"),
    [
        ("2026-01-15", "2026-01-14T23:00:00+00:00", "2026-01-15T22:59:59.999999+00:00"),
        ("2026-03-29", "2026-03-28T23:00:00+00:00", "2026-03-29T21:59:59.999999+00:00"),
        ("2026-10-25", "2026-10-24T22:00:00+00:00", "2026-10-25T22:59:59.999999+00:00"),
    ],
)
def test_intelligence_dates_follow_profile_timezone(authenticated_client, auth_user, responses_mock, route, local_day, utc_start, utc_end):
    user = auth_user.model_copy(deep=True)
    user.profile.timezone = "Europe/Vienna"
    add_user_to_cache(user.model_dump(mode="json"))
    filters = IntelligenceFilters(collected_from=utc_start, collected_to=utc_end, cve_id="CVE-2026-12345")
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{route}",
        json={
            "asset_name": "Host 1",
            "items": [],
            "assets": [],
            "groups": [],
            "tags": [],
            "page": 1,
            "page_size": 20,
            "total_stories": 0,
            "total_articles": 0,
            "filters": filters.model_dump(mode="json", exclude={"page"}),
        },
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assets/host-1/match-runs", json={"run": None})
    response = authenticated_client.get(
        route, query_string={"collected_from": local_day, "collected_to": local_day, "cve_id": "CVE-2026-12345"}
    )
    assert response.status_code == 200
    forwarded = next(call.request.url for call in responses_mock.calls if urlparse(call.request.url).path.endswith(route))
    query = parse_qs(urlparse(forwarded).query)
    assert query["collected_from"] == [utc_start]
    assert query["collected_to"] == [utc_end]
    tree = html.fromstring(response.text)
    assert tree.xpath('//input[@name="collected_from"]/@value') == [local_day]
    assert tree.xpath('//input[@name="collected_to"]/@value') == [local_day]
    assert "Europe/Vienna" in tree.text_content()
    assert "0 matching stories · 0 matching articles" in tree.text_content()
    if route != "/assets/intelligence":
        overview = tree.xpath('//a[normalize-space()="Intelligence overview"]/@href')[0]
        query = parse_qs(urlparse(overview).query)
        assert query["asset_id"] == ["host-1"]
        assert query["collected_from"] == query["collected_to"] == [local_day]
        assert query["cve_id"] == ["CVE-2026-12345"]
