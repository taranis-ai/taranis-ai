from datetime import datetime, timedelta

import pytest
from models.types import COLLECTOR_TYPES
from pydantic import ValidationError

from core.model.osint_source import INVALID_COLLECTION_PERIOD_MESSAGE, OSINTSource


@pytest.mark.usefixtures("app")
def test_osint_source_constructor_validates_rank():
    with pytest.raises(ValidationError, match="less than or equal to 5"):
        OSINTSource(
            name="Invalid Rank",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            rank=6,
        )


@pytest.mark.usefixtures("app")
def test_osint_source_from_dict_accepts_parameter_dict():
    source = OSINTSource.from_dict(
        {
            "name": "Source",
            "description": "A test",
            "type": "rss_collector",
            "parameters": {"FEED_URL": "https://example.com/feed.xml"},
            "news_items_count": 3,
        }
    )

    assert source.parameters["FEED_URL"] == "https://example.com/feed.xml"


@pytest.mark.usefixtures("app")
def test_osint_source_update_validates_rank(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.MANUAL_COLLECTOR,
    )
    session.add(source)
    session.commit()

    with pytest.raises(ValidationError, match="less than or equal to 5"):
        OSINTSource.update(source.id, {"rank": 6})


@pytest.mark.usefixtures("app")
def test_osint_source_partial_update_preserves_unsent_fields(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        parameters={"FEED_URL": "https://example.com/feed.xml"},
    )
    session.add(source)
    session.commit()

    updated_source = OSINTSource.update(source.id, {"description": ""})

    assert updated_source is not None
    assert updated_source.name == "Source"
    assert updated_source.description == ""
    assert updated_source.parameters["FEED_URL"] == "https://example.com/feed.xml"


@pytest.mark.usefixtures("app")
def test_osint_source_partial_update_reparses_parameters(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        parameters={"FEED_URL": "https://example.com/feed.xml"},
    )
    session.add(source)
    session.commit()

    updated_source = OSINTSource.update(source.id, {"parameters": {"FEED_URL": "https://changed.example/feed.xml"}})

    assert updated_source is not None
    assert updated_source.parameters["FEED_URL"] == "https://changed.example/feed.xml"


@pytest.mark.usefixtures("app")
def test_osint_source_to_detail_dict_includes_collection_counts(session, monkeypatch):
    now = datetime(2026, 9, 3, 12)
    monkeypatch.setattr(OSINTSource, "utcnow", staticmethod(lambda: now))
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        parameters={"FEED_URL": "https://example.com/feed.xml"},
    )
    session.add(source)
    session.flush()

    from core.model.news_item import NewsItem

    first = NewsItem(
        title="News Item 1",
        source="source",
        content="content 1",
        osint_source_id=source.id,
        link="https://example.com/1",
        story_id=None,
        collected=now - timedelta(hours=12),
    )
    second = NewsItem(
        title="News Item 2",
        source="source",
        content="content 2",
        osint_source_id=source.id,
        link="https://example.com/2",
        story_id=None,
        collected=now - timedelta(days=3),
    )
    third = NewsItem(
        title="News Item 3",
        source="source",
        content="content 3",
        osint_source_id=source.id,
        link="https://example.com/3",
        story_id=None,
        collected=now - timedelta(days=10),
    )
    session.add_all([first, second, third])
    session.flush()

    assert source.to_detail_dict("day")["collection_count"] == 1
    assert source.to_detail_dict("week")["collection_count"] == 2
    detail = source.to_detail_dict("month")
    assert detail["news_items_count"] == 3
    assert detail["collection_count"] == 3
    assert detail["collection_period"] == "month"


def test_osint_source_detail_rejects_invalid_collection_period(client, auth_header):
    response = client.get("/api/config/osint-sources/missing", query_string={"period": "year"}, headers=auth_header)

    assert response.status_code == 400
    assert response.json == {"error": INVALID_COLLECTION_PERIOD_MESSAGE}
