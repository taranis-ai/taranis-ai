"""Integration tests for task result processing in core API."""

from core.api.task import handle_task_specific_result


class TestTaskResultProcessing:
    def test_bot_tagging_calls_services(self, monkeypatch):
        calls = {"found": None, "execution": 0}

        def fake_set_found_bot_tags(payload, change_by_bot=True):
            calls["found"] = (payload, change_by_bot)

        def fake_set_bot_execution_attribute(payload):
            calls["execution"] += 1

        monkeypatch.setattr("core.api.task.NewsItemTagService.set_found_bot_tags", fake_set_found_bot_tags)
        monkeypatch.setattr("core.api.task.NewsItemTagService.set_bot_execution_attribute", fake_set_bot_execution_attribute)

        result = {
            "bot_type": "WORDLIST_BOT",
            "result": {"tagged_items": 5},
            "news_items": [{"id": "item1", "attributes": []}],
        }

        handle_task_specific_result("bot-job-123", result, "SUCCESS", "bot_bot-456")

        assert calls["found"] == (result, True)
        assert calls["execution"] == 1

    def test_bot_error_logs_and_skips_processing(self, monkeypatch, caplog):
        calls = {"found": 0, "execution": 0}

        monkeypatch.setattr("core.api.task.NewsItemTagService.set_found_bot_tags", lambda *_: calls.__setitem__("found", calls["found"] + 1))
        monkeypatch.setattr(
            "core.api.task.NewsItemTagService.set_bot_execution_attribute", lambda *_: calls.__setitem__("execution", calls["execution"] + 1)
        )

        result = {"bot_type": "IOC_BOT", "result": {"error": "Bot execution failed: Connection timeout"}}

        handle_task_specific_result("bot-job-456", result, "FAILURE", "bot_bot-789")

        assert "Bot execution failed: Connection timeout" in caplog.text
        assert calls["found"] == 0
        assert calls["execution"] == 0

    def test_presenter_updates_product(self, monkeypatch):
        updated = {}

        def fake_update_render_for_id(product_id, rendered_product):
            updated["id"] = product_id
            updated["render"] = rendered_product

        monkeypatch.setattr("core.api.task.Product.update_render_for_id", fake_update_render_for_id)

        result = {"product_id": "prod-789", "message": "ok", "render_result": "YmFzZTY0"}

        handle_task_specific_result("presenter-job-123", result, "SUCCESS", "presenter_task")

        assert updated == {"id": "prod-789", "render": "YmFzZTY0"}

    def test_presenter_missing_fields_logs_error(self, caplog):
        result = {"message": "Product rendered but missing fields"}

        handle_task_specific_result("presenter-job-456", result, "SUCCESS", "presenter_task")

        assert "not found or no render result" in caplog.text

    def test_collector_logs_string_result(self, caplog):
        result = "'RSS Feed': Collected 10 new articles"

        handle_task_specific_result("collector-job-123", result, "SUCCESS", "collect_rss")

        assert "collector-job-123" in caplog.text
        assert "Collected 10 new articles" in caplog.text
