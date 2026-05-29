from datetime import datetime, timedelta

from core.managers.db_manager import db
from core.model.collection_run import CollectionRun, CollectionRunBotCompletion
from core.model.osint_source import OSINTSource
from core.model.story import Story


def _news_item_payload(source_id: str, *, title: str, link: str, content: str) -> dict:
    return {
        "title": title,
        "link": link,
        "content": content,
        "review": f"{title} review",
        "osint_source_id": source_id,
        "source": "https://example.com/feed.xml",
    }


def _reset_collection_runs() -> None:
    db.session.execute(db.delete(CollectionRunBotCompletion))
    db.session.execute(db.delete(CollectionRun))
    db.session.commit()


class TestCollectionRunStatistics:
    base_uri = "/api"

    def test_worker_news_items_collection_run_counts_only_accepted_items(self, client, api_header, app, fake_source):
        with app.app_context():
            _reset_collection_runs()
            existing_item = _news_item_payload(
                fake_source,
                title="Existing item",
                link="https://example.com/existing",
                content="duplicate content",
            )
            Story.add_news_items([existing_item])
            run = CollectionRun.start_run(
                osint_source_id=fake_source,
                collector_job_id="collect-job-accepted",
                collector_type="rss_collector",
            )
            run_id = run.id

        new_item = _news_item_payload(
            fake_source,
            title="New item",
            link="https://example.com/new",
            content="brand new content",
        )
        expected_bytes = len(f"{new_item['title']}{new_item['title']} review{new_item['content']}".encode("utf-8"))

        response = client.post(
            f"{self.base_uri}/worker/news-items",
            json={"collection_run_id": run_id, "items": [existing_item, new_item]},
            headers=api_header,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["accepted_news_items_count"] == 1
        assert payload["stored_bytes"] == expected_bytes

        with app.app_context():
            persisted_run = CollectionRun.get(run_id)
            assert persisted_run is not None
            assert persisted_run.news_items_count == 1
            assert persisted_run.stored_bytes == expected_bytes
            _reset_collection_runs()

    def test_collection_run_pipeline_finishes_without_post_collection_bots(self, app, fake_source):
        with app.app_context():
            _reset_collection_runs()
            run = CollectionRun.start_run(
                osint_source_id=fake_source,
                collector_job_id="collect-job-no-bots",
                collector_type="rss_collector",
            )

            finished = CollectionRun.finish_collector(run.id, collector_status="SUCCESS", expected_post_collection_bots=0)

            assert finished is not None
            assert finished.collector_finished_at is not None
            assert finished.pipeline_finished_at == finished.collector_finished_at
            _reset_collection_runs()

    def test_collection_run_allows_repeated_collector_job_ids(self, app, fake_source):
        with app.app_context():
            _reset_collection_runs()
            first_run = CollectionRun.start_run(
                osint_source_id=fake_source,
                collector_job_id=f"collect_rss_collector_{fake_source}",
                collector_type="rss_collector",
            )
            second_run = CollectionRun.start_run(
                osint_source_id=fake_source,
                collector_job_id=f"collect_rss_collector_{fake_source}",
                collector_type="rss_collector",
            )

            assert first_run.id != second_run.id
            latest_run = CollectionRun.get_by_collector_job_id(f"collect_rss_collector_{fake_source}")
            assert latest_run is not None
            assert latest_run.id == second_run.id
            _reset_collection_runs()

    def test_collection_run_bot_completion_marks_pipeline_finished(self, app, fake_source):
        with app.app_context():
            _reset_collection_runs()
            run = CollectionRun.start_run(
                osint_source_id=fake_source,
                collector_job_id="collect-job-with-bot",
                collector_type="rss_collector",
            )
            finished = CollectionRun.finish_collector(run.id, collector_status="SUCCESS", expected_post_collection_bots=1)

            assert finished is not None
            assert finished.pipeline_finished_at is None

            completed = CollectionRun.record_bot_completion(
                run.id,
                bot_id="00000000-0000-0000-0000-000000000001",
                bot_type="WORDLIST_BOT",
                status="SUCCESS",
            )

            assert completed is not None
            assert completed.pipeline_finished_at is not None
            assert completed.pipeline_finished_at >= completed.collector_finished_at
            _reset_collection_runs()

    def test_collection_run_statistics_summary_and_source_filter(self, client, auth_header, app, fake_source):
        now = datetime(2026, 5, 28, 12, 0, 0)

        with app.app_context():
            _reset_collection_runs()
            manual_source = OSINTSource.get_by_key("manual")
            assert manual_source is not None

            source_runs = [
                CollectionRun(
                    id="00000000-0000-0000-0000-000000000101",
                    osint_source_id=fake_source,
                    collector_job_id="summary-source-run-1",
                    collector_type="rss_collector",
                ),
                CollectionRun(
                    id="00000000-0000-0000-0000-000000000102",
                    osint_source_id=fake_source,
                    collector_job_id="summary-source-run-2",
                    collector_type="rss_collector",
                ),
                CollectionRun(
                    id="00000000-0000-0000-0000-000000000103",
                    osint_source_id=fake_source,
                    collector_job_id="summary-source-run-3",
                    collector_type="rss_collector",
                ),
            ]
            other_run = CollectionRun(
                id="00000000-0000-0000-0000-000000000104",
                osint_source_id=manual_source.id,
                collector_job_id="summary-manual-run-1",
                collector_type="manual_collector",
            )

            source_runs[0].collector_started_at = now - timedelta(hours=3, minutes=5)
            source_runs[0].collector_finished_at = now - timedelta(hours=2, minutes=45)
            source_runs[0].pipeline_finished_at = source_runs[0].collector_started_at + timedelta(seconds=60)
            source_runs[0].collector_status = "SUCCESS"
            source_runs[0].news_items_count = 2
            source_runs[0].stored_bytes = 2048

            source_runs[1].collector_started_at = now - timedelta(hours=3)
            source_runs[1].collector_finished_at = now - timedelta(hours=2, minutes=15)
            source_runs[1].pipeline_finished_at = source_runs[1].collector_started_at + timedelta(seconds=120)
            source_runs[1].collector_status = "SUCCESS"
            source_runs[1].news_items_count = 1
            source_runs[1].stored_bytes = 1024

            source_runs[2].collector_started_at = now - timedelta(hours=6, minutes=10)
            source_runs[2].collector_finished_at = now - timedelta(hours=6)
            source_runs[2].pipeline_finished_at = source_runs[2].collector_started_at + timedelta(seconds=240)
            source_runs[2].collector_status = "SUCCESS"
            source_runs[2].news_items_count = 2
            source_runs[2].stored_bytes = 3072

            other_run.collector_started_at = now - timedelta(hours=1, minutes=10)
            other_run.collector_finished_at = now - timedelta(hours=1)
            other_run.pipeline_finished_at = other_run.collector_started_at + timedelta(seconds=30)
            other_run.collector_status = "SUCCESS"
            other_run.news_items_count = 4
            other_run.stored_bytes = 4096

            db.session.add_all(source_runs + [other_run])
            db.session.commit()

        response = client.get(f"{self.base_uri}/config/osint-source-statistics", headers=auth_header)
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["items_24h"] == 9
        assert payload["stored_kb_24h"] == 10.0

        response = client.get(
            f"{self.base_uri}/config/osint-source-statistics",
            headers=auth_header,
            query_string={"source_id": fake_source},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["items_24h"] == 5
        assert payload["stored_kb_24h"] == 6.0
        assert payload["peak_hour_items"] == 3
        assert payload["peak_hour_stored_kb"] == 3.0
        assert payload["latency_avg_seconds"] == 140.0
        assert payload["latency_p95_seconds"] == 240
        assert payload["latency_max_seconds"] == 240
        assert payload["latency_sample_runs"] == 3
        assert payload["peak_hour_started_at"] is not None

        with app.app_context():
            _reset_collection_runs()

    def test_collection_run_statistics_summary_empty_state(self, client, auth_header, app):
        with app.app_context():
            _reset_collection_runs()

        response = client.get(f"{self.base_uri}/config/osint-source-statistics", headers=auth_header)

        assert response.status_code == 200
        assert response.get_json() == {
            "items_24h": 0,
            "stored_kb_24h": 0.0,
            "peak_hour_started_at": None,
            "peak_hour_items": 0,
            "peak_hour_stored_kb": 0.0,
            "latency_avg_seconds": None,
            "latency_p95_seconds": None,
            "latency_max_seconds": None,
            "latency_sample_runs": 0,
        }
