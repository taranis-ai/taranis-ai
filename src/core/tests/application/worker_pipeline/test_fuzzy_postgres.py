from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from sqlalchemy import event, text
from yoyo import get_backend, read_migrations

from core.config import Config
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story
from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story


def test_concurrent_collection_serializes_source_check_and_insert(postgres_fuzzy_app, monkeypatch):
    monkeypatch.setattr(Config, "FUZZY_DEDUP_ENABLED", True)
    body = (Path(__file__).parents[2] / "test_data" / "fuzzy_article.txt").read_text()
    with postgres_fuzzy_app.app_context():
        source_id = create_osint_source(rank=0, name="Concurrent collection").id
        engine = db.engine
    payloads = [build_news_item_payload(source_id, content=body) for _ in range(2)]
    barrier = Barrier(2)

    def synchronize_checks(conn, cursor, statement, parameters, context, executemany):
        if "osint_source" in statement and statement.endswith("FOR UPDATE"):
            barrier.wait(timeout=10)

    def collect(payload):
        with postgres_fuzzy_app.app_context():
            return Story.add_news_items([payload], collection=True)

    event.listen(engine, "before_cursor_execute", synchronize_checks)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(collect, payloads))
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_checks)
    assert all(status == 200 for _, status in results), results
    assert sorted(len(result["news_item_ids"]) for result, _ in results) == [0, 1]
    with postgres_fuzzy_app.app_context():
        assert db.session.query(NewsItem).count() == 1


def test_released_schema_upgrade_preserves_items_and_can_roll_back(postgres_fuzzy_app):
    with postgres_fuzzy_app.app_context():
        source_id = create_osint_source(rank=0, name="Migration source").id
        item = create_story(news_items=[build_news_item_payload(source_id)]).news_items[0]
        item_id, item_hash = item.id, item.hash
        db.session.remove()
        with db.engine.begin() as connection:
            connection.execute(text("DROP INDEX ix_news_item_source_collected"))
            connection.execute(text("ALTER TABLE news_item DROP COLUMN fuzzy_hash"))

        migrations = read_migrations("migrations").filter(lambda migration: migration.id == "20260911_01_f8H2q-add-news-item-fuzzy-hash")
        backend = get_backend(postgres_fuzzy_app.config["SQLALCHEMY_DATABASE_URI"])
        try:
            backend.apply_migrations(migrations)
            migrated = NewsItem.get(item_id)
            assert migrated.hash == item_hash
            assert migrated.fuzzy_hash is None
            db.session.remove()
            backend.rollback_migrations(migrations)
            with db.engine.connect() as connection:
                assert connection.execute(text("SELECT hash FROM news_item WHERE id = :id"), {"id": item_id}).scalar_one() == item_hash
            backend.apply_migrations(migrations)
            assert NewsItem.get(item_id).fuzzy_hash is None
        finally:
            backend.connection.close()
