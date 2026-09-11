from datetime import timedelta
from pathlib import Path

import ppdeep
import pytest
from click.testing import CliRunner

from core.cli import main
from core.config import Config
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story
from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story


@pytest.fixture
def article():
    return (Path(__file__).parents[2] / "test_data" / "fuzzy_article.txt").read_text()


@pytest.fixture
def fuzzy_source(session, monkeypatch):
    monkeypatch.setattr(Config, "FUZZY_DEDUP_ENABLED", True)
    return create_osint_source(rank=0, name="Fuzzy ingestion source")


def test_collection_deduplicates_normalized_and_near_identical_bodies(client, api_header, fuzzy_source, article):
    original = build_news_item_payload(fuzzy_source.id, content=article)
    whitespace = build_news_item_payload(fuzzy_source.id, content=article.replace(" ", "\u00a0  "))
    revised = build_news_item_payload(fuzzy_source.id, content=article.replace("on Tuesday", "on Wednesday"))
    for payload in (original, whitespace, revised):
        payload["fuzzy_hash"] = "untrusted fingerprint"

    response = client.post("/api/worker/news-items", json=[original, whitespace, revised], headers=api_header)
    assert response.status_code == 200
    assert response.json["news_item_ids"] == [original["id"]]
    assert response.json["warning"] == "2 items were skipped"
    item = NewsItem.get(original["id"])
    assert item.fuzzy_hash == NewsItem.get_fuzzy_hash(article)
    assert "fuzzy_hash" not in item.to_dict()
    assert "fuzzy_hash" not in item.story.to_worker_dict()["news_items"][0]

    response = client.post("/api/worker/news-items", json=[revised], headers=api_header)
    assert response.status_code == 200
    assert response.json["message"] == "All news items were skipped"

    # Explicit creation and synchronized story ingestion keep their own identity rules.
    result, status = Story.add_single_news_item(whitespace)
    assert status == 200
    assert result["news_item_ids"] == [whitespace["id"]]
    result, status = Story.add_or_update({"title": "External event", "news_items": [revised]})
    assert status == 200
    assert result["news_item_ids"] == [revised["id"]]


@pytest.mark.parametrize(
    "candidate_age, expected", [(timedelta(days=30), 0), (timedelta(days=30, microseconds=1), 1), (timedelta(days=-1), 1)]
)
def test_collection_window_uses_utc_collected_time(client, api_header, fuzzy_source, article, monkeypatch, candidate_age, expected):
    now = NewsItem.utcnow()
    monkeypatch.setattr(NewsItem, "utcnow", staticmethod(lambda: now))
    candidate = build_news_item_payload(fuzzy_source.id, content=article)
    candidate["collected"] = (now - candidate_age).isoformat() + "Z"
    candidate["published"] = (now - timedelta(days=365)).isoformat() + "Z"
    create_story(news_items=[candidate])
    incoming = build_news_item_payload(fuzzy_source.id, content=article)
    response = client.post("/api/worker/news-items", json=[incoming], headers=api_header)
    assert response.status_code == 200
    assert len(response.json["news_item_ids"]) == expected


def test_collection_preserves_other_sources_short_bodies_and_disabled_mode(client, api_header, fuzzy_source, article, monkeypatch):
    original = build_news_item_payload(fuzzy_source.id, content=article)
    create_story(news_items=[original])
    other_source = create_osint_source(rank=1, name="Other fuzzy source")
    payloads = [
        build_news_item_payload(other_source.id, content=article),
        build_news_item_payload("manual", content=article),
        build_news_item_payload("missing-source", content=article),
        build_news_item_payload(fuzzy_source.id, content="Short bulletin"),
        build_news_item_payload(fuzzy_source.id, content="Short bulletin"),
        build_news_item_payload(fuzzy_source.id) | {"content": ""},
    ]
    response = client.post("/api/worker/news-items", json=payloads, headers=api_header)
    assert response.status_code == 200
    assert len(response.json["news_item_ids"]) == len(payloads)
    assert NewsItem.get(payloads[-1]["id"]).fuzzy_hash is None

    monkeypatch.setattr(Config, "FUZZY_DEDUP_ENABLED", False)
    incoming = build_news_item_payload(fuzzy_source.id, content=article)
    response = client.post("/api/worker/news-items", json=[incoming, original], headers=api_header)
    assert response.status_code == 200
    assert response.json["news_item_ids"] == [incoming["id"]]


def test_fingerprints_refresh_after_edits_and_backfill_preserves_timestamps(app, fuzzy_source, article, monkeypatch):
    manual = create_story(news_items=[build_news_item_payload(content=article)]).news_items[0]
    before = manual.fuzzy_hash
    revised = article.replace("gateway", "router")
    _, status = manual.update_item({"content": revised})
    assert status == 200
    assert manual.fuzzy_hash == NewsItem.get_fuzzy_hash(revised) != before

    old = build_news_item_payload(fuzzy_source.id, content=article)
    old["collected"] = (NewsItem.utcnow() - timedelta(days=31)).isoformat()
    recent = build_news_item_payload(fuzzy_source.id, content=article)
    short = build_news_item_payload(fuzzy_source.id, content="Short bulletin")
    items = create_story(news_items=[old, recent, short]).news_items
    for item in items:
        item.fuzzy_hash = None
    db.session.commit()
    timestamps = {item.id: (item.updated, item.collected, item.published) for item in items}

    monkeypatch.setattr("core.cli.create_app", lambda **kwargs: app)
    runner = CliRunner()
    result = runner.invoke(main, ["backfill-fuzzy-hashes", "--batch-size", "1"])
    assert result.exit_code == 0, result.output
    assert "filled 1 fingerprints" in result.output
    db.session.expire_all()
    assert NewsItem.get(recent["id"]).fuzzy_hash == NewsItem.get_fuzzy_hash(article)
    assert NewsItem.get(old["id"]).fuzzy_hash is None
    assert NewsItem.get(short["id"]).fuzzy_hash is None
    refreshed = [NewsItem.get(item_id) for item_id in timestamps]
    assert {item.id: (item.updated, item.collected, item.published) for item in refreshed} == timestamps
    result = runner.invoke(main, ["backfill-fuzzy-hashes", "--batch-size", "1"])
    assert result.exit_code == 0, result.output
    assert "filled 0 fingerprints" in result.output


def test_ctph_vectors_and_article_similarity(article):
    # Published ssdeep reference vector, independent of the application's normalizer.
    assert ppdeep.hash("Also called fuzzy hashes, Ctph can match inputs that have homologies.") == "3:AXGBicFlgVNhBGcL6wCrFQEv:AXGHsNhxLsr2C"
    fingerprint = NewsItem.get_fuzzy_hash(article)
    assert ppdeep.compare(fingerprint, NewsItem.get_fuzzy_hash(article.replace("on Tuesday", "on Wednesday"))) >= 90
    unrelated = " ".join(reversed(article.split()))
    assert ppdeep.compare(fingerprint, NewsItem.get_fuzzy_hash(unrelated)) < 90
    assert NewsItem.get_fuzzy_hash(article + " cafe\u0301") == NewsItem.get_fuzzy_hash(article + " café")
