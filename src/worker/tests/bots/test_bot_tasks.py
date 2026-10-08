"""Tests for bot task execution and result handling."""

import json
import re
import traceback
from unittest.mock import patch

# pyright: reportMissingParameterType=false
import pytest
from fakeredis import FakeRedis
from llm_bot.client import LLMClient, UpstreamLLMError
from models.task import TaskResult
from niquests.exceptions import RequestException
from rq import Queue, SimpleWorker
from rq.job import JobStatus

import worker.bots
from worker.bots.bot_tasks import bot_task
from worker.config import Config
from worker.core_api import CoreApi, build_success_task_result


BOT_CLASS_NAMES = [
    "AnalystBot",
    "GroupingBot",
    "TaggingBot",
    "WordlistBot",
    "NLPBot",
    "StoryBot",
    "IOCBot",
    "SummaryBot",
    "SentimentAnalysisBot",
    "CyberSecClassifierBot",
]


@pytest.fixture
def current_job(monkeypatch, mock_job):
    monkeypatch.setattr("worker.bots.bot_tasks.get_current_job", lambda: mock_job)
    return mock_job


@pytest.fixture
def no_current_job(monkeypatch):
    monkeypatch.setattr("worker.bots.bot_tasks.get_current_job", lambda: None)


@pytest.fixture
def batch_queue():
    return Queue("bots", connection=FakeRedis())


@pytest.fixture
def bot_config():
    """Sample bot configuration."""
    return {
        "id": "bot-456",
        "type": "wordlist_bot",
        "name": "Test Bot",
        "parameters": {"ITEM_FILTER": "limit=5"},
    }


@pytest.fixture
def stub_bots(monkeypatch):
    class DummyBot:
        _execute_impl = staticmethod(lambda params: {"message": "ok"})

        def execute(self, params):
            return type(self)._execute_impl(params)

    for class_name in BOT_CLASS_NAMES:
        monkeypatch.setattr(worker.bots, class_name, DummyBot)

    return DummyBot


class TestBotTask:
    """Tests for bot_task function."""

    @pytest.mark.parametrize("api_format", ["chat_completions", "responses"])
    @pytest.mark.parametrize("bot_type", ["story_bot", "summary_bot", "nlp_bot", "sentiment_analysis_bot", "cybersec_classifier_bot"])
    def test_batch_bot_waits_then_applies_results(
        self,
        batch_queue,
        requests_mock,
        stories,
        story_update_mock,
        story_attribute_update_mock,
        news_item_attribute_update_mock,
        bot_type,
        api_format,
    ):
        endpoint = {
            "name": "Batch model",
            "base_url": "https://batch.test/api/v1",
            "model": "deepseek/deepseek-v4.1-flash:batch",
            "api_key": "batch-key",
            "processing_mode": "openrouter_batch",
            "api_format": api_format,
        }
        config = requests_mock.get(
            f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456",
            json={"type": bot_type, "parameters": {}, "llm_endpoint": endpoint},
        )
        inputs = [{**story, "summary": f"Story {index}", "tags": {}} for index, story in enumerate(stories[:2])]
        loaded = requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=inputs)
        grouped = requests_mock.put(f"{Config.TARANIS_CORE_URL}/bots/stories/group-multiple", json={"message": "success"})
        saved = requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        batches = {}

        def submit(request, context):
            payload = request.json()
            assert list(payload) == ["endpoint", "model", "requests"]
            assert payload["model"] == endpoint["model"]
            assert payload["endpoint"] == ("/v1/chat/completions" if api_format == "chat_completions" else "/v1/responses")
            assert request.headers["Authorization"] == "Bearer batch-key"
            batch_id = f"batch_{len(batches)}"
            batches[batch_id] = payload["requests"]
            context.status_code = 202
            return {"id": batch_id, "status": "validating"}

        submitted = requests_mock.post(f"{endpoint['base_url']}/batches", json=submit)
        status_url = re.compile(r"https://batch.test/api/v1/batches/batch_\d+")
        requests_mock.get(status_url, json={"status": "in_progress", "results": None})
        job = batch_queue.enqueue(bot_task, "bot-456")
        dependent = batch_queue.enqueue("builtins.len", [1], depends_on=job)
        worker = SimpleWorker([batch_queue], connection=batch_queue.connection)
        worker.work(burst=True, logging_level="WARNING")
        assert job.get_status(refresh=True) == JobStatus.SCHEDULED
        assert dependent.get_status(refresh=True) == JobStatus.DEFERRED
        assert saved.call_count == 0
        assert sum(len(requests) for requests in batches.values()) > (1 if bot_type != "story_bot" else 0)

        # A new worker uses persisted inputs/configuration, even after administrators edit them.
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json={"type": "wordlist_bot"})
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=[])
        batch_queue.scheduled_job_registry.remove(job)
        batch_queue.enqueue_job(job)
        worker.work(burst=True, logging_level="WARNING")
        assert job.get_status(refresh=True) == JobStatus.SCHEDULED
        assert dependent.get_status(refresh=True) == JobStatus.DEFERRED
        assert saved.call_count == 0
        assert submitted.call_count == len(batches)

        outputs = {
            "summary_response": {"summary": "Concise batch summary"},
            "title_response": {"title": "Batch title"},
            "ner_response": {"Microsoft": "ORG"},
            "sentiment_response": {"sentiment": {"label": "neutral", "score": 0.49}},
            "cybersec_classification_response": {"cybersecurity": 0.9, "non-cybersecurity": 0.1},
            "cluster_response": {
                "cluster_ids": {"event_clusters": [[1, 2]]},
                "cluster_reasons": [{"story_ids": [1, 2], "reason": "Same event"}],
                "message": "Processed",
            },
        }

        def complete(request, context):
            results = []
            batch_id = request.url.rsplit("/", 1)[-1]
            for item in reversed(batches[batch_id]):
                body = item["body"]
                schema = body["response_format"]["json_schema"] if api_format == "chat_completions" else body["text"]["format"]
                output = {"summary": []} if schema["name"] == "summary_response" and batch_id == "batch_0" else outputs[schema["name"]]
                text = json.dumps(output)
                response = (
                    {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
                    if api_format == "chat_completions"
                    else {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
                )
                results.append({"custom_id": item["custom_id"], "response": {"status_code": 200, "body": response}, "error": None})
            return {"status": "completed", "results": results}

        requests_mock.get(status_url, json=complete)
        batch_queue.scheduled_job_registry.remove(job)
        batch_queue.enqueue_job(job)
        worker.work(burst=True, logging_level="WARNING")
        if bot_type == "summary_bot":
            assert job.get_status(refresh=True) == JobStatus.SCHEDULED
            assert dependent.get_status(refresh=True) == JobStatus.DEFERRED
            assert saved.call_count == story_update_mock.call_count == 0
            batch_queue.scheduled_job_registry.remove(job)
            batch_queue.enqueue_job(job)
            worker.work(burst=True, logging_level="WARNING")
        assert job.get_status(refresh=True) == JobStatus.FINISHED
        assert dependent.get_status(refresh=True) == JobStatus.FINISHED
        assert saved.call_count == 1
        assert saved.last_request.json()["status"] == "SUCCESS"
        assert "llm_batch" not in job.meta
        assert "batch-key" not in str(saved.last_request.json())
        assert config.call_count == loaded.call_count == 1
        if bot_type == "story_bot":
            assert grouped.last_request.json() == [[story["id"] for story in inputs]]
        elif bot_type == "summary_bot":
            assert all(request.json()["summary"] == "Concise batch summary" for request in story_update_mock.request_history)
        elif bot_type == "nlp_bot":
            assert all(value == {"Microsoft": "ORG"} for value in saved.last_request.json()["result"]["data"]["result"].values())
        else:
            assert news_item_attribute_update_mock.call_count > 0

    @pytest.mark.parametrize(
        "failure", [RequestException("private provider detail"), UpstreamLLMError("private provider detail"), None, "unconfigured"]
    )
    @pytest.mark.parametrize("bot_type", ["story_bot", "summary_bot", "nlp_bot", "sentiment_analysis_bot", "cybersec_classifier_bot"])
    def test_llm_bot_failure_is_safe(self, current_job, requests_mock, failure, bot_type):
        requests_mock.real_http = False
        requests_mock.get(
            f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456",
            json={
                "type": bot_type,
                "parameters": {},
                "llm_endpoint": None if failure == "unconfigured" else {"name": "Test", "base_url": "https://llm.test/v1"},
            },
        )
        requests_mock.get(
            f"{Config.TARANIS_CORE_URL}/worker/stories",
            json=[{"id": "story-1", "tags": {}, "news_items": [{"id": "item-1", "title": "Story", "content": "Content"}]}],
        )
        saved = requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        with patch.object(LLMClient, "create_response", autospec=True, side_effect=failure) as provider:
            provider.return_value = {"output_text": "private invalid provider output"}
            with pytest.raises(RuntimeError) as exc_info:
                bot_task("bot-456")

        assert "private" not in "".join(traceback.format_exception(exc_info.value))
        task_data = saved.last_request.json()
        assert task_data["status"] == "FAILURE"
        if failure == "unconfigured":
            assert task_data["result"]["reason"] == "llm_not_configured"
            assert task_data["result"]["retryable"] is False
            assert "Admin Settings > LLM Endpoints" in task_data["result"]["message"]
        else:
            assert task_data["result"]["reason"] == ("bot_service_unavailable" if failure else "bot_execution_failed")
            assert task_data["result"]["retryable"] is bool(failure)
            if failure:
                assert task_data["result"]["message"] == (
                    "Bot service is unavailable. Check its configured endpoint and ensure the service is running."
                )
        assert "private" not in str(task_data["result"])
        assert not any("/worker/llm-endpoints/" in req.url for req in requests_mock.request_history)

    @pytest.mark.parametrize("status", ["failed", "expired", "cancelled", "completed"])
    def test_batch_failure_keeps_dependents_waiting(self, batch_queue, requests_mock, status, news_item_attribute_update_mock):
        requests_mock.get(
            f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456",
            json={
                "type": "sentiment_analysis_bot",
                "parameters": {},
                "llm_endpoint": {
                    "name": "Batch",
                    "base_url": "https://batch.test/v1",
                    "model": "batch-model",
                    "processing_mode": "openrouter_batch",
                },
            },
        )
        requests_mock.get(
            f"{Config.TARANIS_CORE_URL}/worker/stories",
            json=[
                {
                    "id": "story-1",
                    "news_items": [{"id": "item-1", "content": "Text"}],
                }
            ],
        )
        saved = requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        submitted = requests_mock.post("https://batch.test/v1/batches", status_code=202, json={"id": "batch_test", "status": "validating"})
        job = batch_queue.enqueue(bot_task, "bot-456")
        dependent = batch_queue.enqueue("builtins.len", [1], depends_on=job)
        worker = SimpleWorker([batch_queue], connection=batch_queue.connection)
        worker.work(burst=True, logging_level="WARNING")
        assert saved.call_count == 0
        custom_id = submitted.last_request.json()["requests"][0]["custom_id"]
        requests_mock.get(
            "https://batch.test/v1/batches/batch_test",
            json={
                "status": status,
                "error": {"message": "private provider detail"} if status != "completed" else None,
                "results": [{"custom_id": custom_id, "error": {"message": "private per-request detail"}}] if status == "completed" else None,
            },
        )
        batch_queue.scheduled_job_registry.remove(job)
        batch_queue.enqueue_job(job)
        worker.work(burst=True, logging_level="WARNING")
        assert job.get_status(refresh=True) == JobStatus.FAILED
        assert dependent.get_status(refresh=True) == JobStatus.DEFERRED
        assert saved.call_count == 1
        assert saved.last_request.json()["result"]["reason"] == "llm_batch_failed"
        assert "private" not in str(saved.last_request.json())
        assert "private" not in job.exc_info
        assert news_item_attribute_update_mock.call_count == 0

    def test_bot_task_success_passes_result_dict(self, current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task passes the full result dict to CoreApi.save_task_result on success."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "ok"})

        # Mock bot execution result - bot returns a flat result payload
        bot_execution_result = {
            "tagged_items": 5,
            "tags_applied": ["malware", "apt"],
            "news_items": [{"id": "item1"}, {"id": "item2"}],
        }
        stub_bots._execute_impl = staticmethod(lambda params: bot_execution_result)

        # Execute
        result = bot_task("bot-456", {"story_id": "123"})

        # Verify result dict (not message string) is saved
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "test-job-123"
        assert task_data["task"] == "bot_bot-456"
        assert task_data["status"] == "SUCCESS"
        assert task_data["worker_id"] == "bot-456"
        assert task_data["worker_type"] == "WORDLIST_BOT"
        assert isinstance(task_data["result"], dict)
        assert task_data["result"] == {
            "message": "Bot bot-456 executed successfully",
            "reason": None,
            "retryable": False,
            "data": {
                "bot_id": "bot-456",
                "filter": {"story_id": "123"},
                "trigger_dependents": True,
                "result": bot_execution_result,
            },
        }

        # Verify return value includes worker metadata
        assert result["worker_id"] == "bot-456"
        assert result["worker_type"] == "WORDLIST_BOT"
        assert result["tagged_items"] == 5
        assert result["tags_applied"] == ["malware", "apt"]
        assert result["news_items"] == [{"id": "item1"}, {"id": "item2"}]

    def test_bot_task_not_found_wraps_error_in_dict(self, current_job, requests_mock):
        """Test that bot_task wraps error messages in dict when bot not found."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-999", status_code=404, json={"error": "not found"})
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

        # Execute and expect exception
        with pytest.raises(ValueError, match="Bot with id bot-999 not found"):
            bot_task("bot-999")

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert task_data["worker_id"] == "bot-999"
        assert task_data["worker_type"] == "BOT_TASK"
        assert isinstance(task_data["result"], dict)
        assert task_data["result"]["message"] == "Bot with id bot-999 not found"
        assert task_data["result"]["reason"] == "bot_not_found"
        assert task_data["result"]["data"] == {"bot_id": "bot-999", "filter": None, "trigger_dependents": True}

    def test_bot_task_exception_wraps_error_in_dict(self, current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task does not expose unexpected exception messages."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

        def _raise(*_):
            raise RuntimeError("Bot execution crashed")

        stub_bots._execute_impl = staticmethod(_raise)

        # Execute and expect exception
        with pytest.raises(RuntimeError, match="Bot execution crashed"):
            bot_task("bot-456")

        # Verify error is wrapped in dict
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert task_data["worker_id"] == "bot-456"
        assert task_data["worker_type"] == "WORDLIST_BOT"
        assert isinstance(task_data["result"], dict)
        assert task_data["result"]["message"] == "Bot execution failed"
        assert task_data["result"]["reason"] == "bot_execution_failed"

    def test_bot_task_none_result_is_reported_as_failure(self, current_job, requests_mock, bot_config, stub_bots):
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        stub_bots._execute_impl = staticmethod(lambda params: None)

        with pytest.raises(RuntimeError, match="Bot bot-456 returned no result"):
            bot_task("bot-456")

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["status"] == "FAILURE"
        assert task_data["worker_id"] == "bot-456"
        assert task_data["worker_type"] == "WORDLIST_BOT"
        assert task_data["result"] == {
            "message": "Bot bot-456 returned no result",
            "reason": "bot_empty_result",
            "retryable": False,
            "data": {"bot_id": "bot-456", "filter": None, "trigger_dependents": True},
        }

    def test_bot_task_can_suppress_dependent_triggers(self, current_job, requests_mock, bot_config, stub_bots):
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-456", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "ok"})
        stub_bots._execute_impl = staticmethod(lambda params: {"tagged_items": 1})

        bot_task("bot-456", {"SOURCE": "source-1"}, trigger_dependents=False)

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        task_data = put_calls[0].json()
        assert task_data["result"]["data"] == {
            "bot_id": "bot-456",
            "filter": {"SOURCE": "source-1"},
            "trigger_dependents": False,
            "result": {"tagged_items": 1},
        }

    def test_bot_task_without_job_uses_fallback_id(self, no_current_job, requests_mock, bot_config, stub_bots):
        """Test that bot_task uses fallback task_id when no RQ job exists."""
        requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/bots/bot-789", json=bot_config)
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        stub_bots._execute_impl = staticmethod(lambda params: {"message": "success"})

        # Execute
        bot_task("bot-789")

        # Verify fallback ID is used
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "bot_bot-789"


class TestSaveTaskResult:
    """Tests for CoreApi.save_task_result helper."""

    def test_save_task_result_accepts_dict(self, requests_mock):
        """Test that save_task_result accepts a dict parameter."""
        result_dict = {"message": "IOC scan complete", "reason": None, "retryable": False, "data": {"iocs_found": 10}}

        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        CoreApi().save_task_result("job-123", "bot_ioc", "SUCCESS", worker_id="bot-123", worker_type="IOC_BOT", **result_dict)

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        assert put_calls[0].json() == {
            "id": "job-123",
            "task": "bot_ioc",
            "worker_id": "bot-123",
            "worker_type": "IOC_BOT",
            "result": result_dict,
            "status": "SUCCESS",
        }

    def test_save_task_result_formats_payload_correctly(self, requests_mock):
        """Test that save_task_result formats the API payload correctly."""
        result = {"message": "Something went wrong", "reason": "bot_failure", "retryable": False, "data": None}

        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        CoreApi().save_task_result("job-456", "bot_test", "FAILURE", **result)

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        task_data = put_calls[0].json()
        assert task_data["id"] == "job-456"
        assert task_data["task"] == "bot_test"
        assert task_data["result"] == result
        assert task_data["status"] == "FAILURE"

    def test_save_task_result_uses_current_job_user_id_when_missing(self, requests_mock, monkeypatch):
        class DummyJob:
            meta = {"user_id": "user-123"}

        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
        monkeypatch.setattr("worker.core_api.get_current_job", lambda: DummyJob())

        CoreApi().save_task_result("job-user", "collector_task", "SUCCESS", message="ok")

        post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(post_calls) == 1
        assert post_calls[0].json()["user_id"] == "user-123"

    @pytest.mark.parametrize(
        "result_payload",
        [
            {"message": "", "reason": None, "retryable": False, "data": []},
            {"message": "done", "reason": None, "retryable": False, "data": False},
        ],
    )
    def test_save_task_result_preserves_direct_result_payloads(self, requests_mock, result_payload):
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})

        CoreApi().save_task_result("job-direct", "collector_preview", "SUCCESS", result=result_payload)

        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1
        assert put_calls[0].json()["result"] == result_payload

    def test_save_task_result_handles_api_failure_gracefully(self, requests_mock, caplog):
        """Test that save_task_result handles API call failures without raising."""
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", exc=RequestException("API connection failed"))

        # Should not raise, just log
        CoreApi().save_task_result("job-789", "bot_error", "SUCCESS", message="data")

        # Verify error was logged
        assert any("Failed to save task result" in record.message for record in caplog.records)

    def test_save_task_result_handles_api_false_response(self, requests_mock):
        """Test that save_task_result handles False response from API."""
        requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", status_code=500, json={"error": "nope"})

        # Should not raise, API returned False meaning failure
        CoreApi().save_task_result("job-999", "bot_fail", "SUCCESS", message="data")

        # Verify API was called
        put_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
        assert len(put_calls) == 1

    def test_build_success_task_result_merges_dict_output(self):
        task_result = build_success_task_result(
            default_message="Published product",
            output={"message": "Published", "url": "https://example.com"},
            base_data={"product_id": "product-1"},
        )

        assert isinstance(task_result, TaskResult)
        assert task_result.model_dump(mode="json", exclude_none=False) == {
            "message": "Published",
            "reason": None,
            "retryable": False,
            "data": {
                "product_id": "product-1",
                "message": "Published",
                "url": "https://example.com",
            },
        }

    def test_build_success_task_result_keeps_nested_result_when_requested(self):
        task_result = build_success_task_result(
            default_message="Bot finished",
            output={"tagged_items": 5},
            base_data={"bot_id": "bot-1"},
            merge_dict_data=False,
        )

        assert isinstance(task_result, TaskResult)
        assert task_result.model_dump(mode="json", exclude_none=False) == {
            "message": "Bot finished",
            "reason": None,
            "retryable": False,
            "data": {
                "bot_id": "bot-1",
                "result": {"tagged_items": 5},
            },
        }

    def test_build_success_task_result_handles_none_output(self):
        task_result = build_success_task_result(
            default_message="Done",
            output=None,
            base_data={"bot_id": "bot-1"},
            none_message="Bot finished without details",
        )

        assert isinstance(task_result, TaskResult)
        assert task_result.model_dump(mode="json", exclude_none=False) == {
            "message": "Bot finished without details",
            "reason": None,
            "retryable": False,
            "data": {"bot_id": "bot-1"},
        }
