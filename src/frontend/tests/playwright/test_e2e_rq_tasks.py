import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
import redis
from rq import Queue
from rq.job import Job
from rq.results import Result

from tests.core_requests import CoreRequestClient


CRON_ENQUEUE_KEY_PREFIX = "rq:cron:enqueue:"
DEFAULT_JOB_TIMEOUT_SECONDS = 30
CRON_JOB_TIMEOUT_SECONDS = 90

RedisBackend = dict[str, str]
JsonDict = dict[str, Any]


def _parse_cron_spec(raw_spec: object) -> dict[str, Any]:
    if isinstance(raw_spec, bytes):
        raw_text = raw_spec.decode()
    elif isinstance(raw_spec, str):
        raw_text = raw_spec
    else:
        raise TypeError(f"Unsupported cron spec payload type: {type(raw_spec)!r}")

    parsed = json.loads(raw_text)
    assert isinstance(parsed, dict), f"Expected cron spec to decode to a dict, got {type(parsed)!r}"
    return parsed


def _redis_conn(redis_backend: RedisBackend) -> redis.Redis:
    return redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)


def _decode_redis_string(raw_value: bytes | str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.decode() if isinstance(raw_value, bytes) else raw_value


def _cron_enqueue_key(job_id: str) -> str:
    return f"{CRON_ENQUEUE_KEY_PREFIX}{job_id}"


def _wait_for_job_result(
    redis_backend: RedisBackend,
    job_id: str,
    timeout_seconds: int = DEFAULT_JOB_TIMEOUT_SECONDS,
) -> Result:
    job = Job.fetch(job_id, connection=_redis_conn(redis_backend))
    result = job.latest_result(timeout=timeout_seconds)
    if result is None:
        raise RuntimeError(f"Timed out waiting for RQ result stream for job {job_id}")
    if result.type == Result.Type.FAILED:
        raise RuntimeError(f"Job {job_id} failed: {result.exc_string}")
    return result


def _get_latest_result_marker(redis_backend: RedisBackend, job_id: str) -> str | None:
    redis_conn = _redis_conn(redis_backend)
    entries = redis_conn.xrevrange(Result.get_key(job_id), count=1)
    if not entries:
        return None

    result_id, _ = entries[0]  # type: ignore[assignment]
    return _decode_redis_string(result_id)


def _wait_for_next_job_result(
    redis_backend: RedisBackend,
    job_id: str,
    previous_result_id: str | None,
    timeout_seconds: int = DEFAULT_JOB_TIMEOUT_SECONDS,
) -> Result:
    redis_conn = _redis_conn(redis_backend)
    stream_key = Result.get_key(job_id)
    if latest_entries := redis_conn.xrevrange(stream_key, count=1):
        result_id, payload = latest_entries[0]  # type: ignore[assignment]
        decoded_result_id = _decode_redis_string(result_id)
        if decoded_result_id and decoded_result_id != previous_result_id:
            return _restore_result_or_raise(job_id, decoded_result_id, payload, redis_conn)
    start_id = previous_result_id or "$"
    response = redis_conn.xread({stream_key: start_id}, block=timeout_seconds * 1000)
    if not response:
        raise RuntimeError(f"Timed out waiting for a fresh RQ result stream entry for job {job_id}")

    _, entries = response[0]  # type: ignore[assignment]
    result_id, payload = entries[-1]
    decoded_result_id = _decode_redis_string(result_id)
    if not decoded_result_id:
        raise RuntimeError(f"Received an empty result stream id for job {job_id}")
    return _restore_result_or_raise(job_id, decoded_result_id, payload, redis_conn)


def _restore_result_or_raise(
    job_id: str,
    decoded_result_id: str,
    payload: Any,
    redis_conn: redis.Redis,
) -> Result:
    result = Result.restore(job_id, decoded_result_id, payload, connection=redis_conn)
    if result.type == Result.Type.FAILED:
        raise RuntimeError(f"Job {job_id} failed: {result.exc_string}")
    return result


def _assert_cron_registration(
    redis_backend: RedisBackend,
    job_id: str,
    expected_cron: str | None = None,
) -> tuple[dict[str, Any], float]:
    redis_conn = _redis_conn(redis_backend)
    raw_spec = redis_conn.hget("rq:cron:def", job_id)
    next_run_raw = redis_conn.zscore("rq:cron:next", job_id)
    assert isinstance(raw_spec, (bytes, str)), f"Missing cron registration for {job_id}"
    assert isinstance(next_run_raw, (int, float)), f"Missing or invalid next run entry for {job_id}"
    next_run = float(next_run_raw)
    parsed = _parse_cron_spec(raw_spec)
    if expected_cron is not None:
        assert parsed.get("cron") == expected_cron
    return parsed, next_run


def _wait_for_cron_enqueue_event(
    redis_backend: RedisBackend,
    cron_job_id: str,
    timeout_seconds: int = CRON_JOB_TIMEOUT_SECONDS,
) -> str:
    redis_conn = _redis_conn(redis_backend)
    result: tuple[bytes, bytes] | None = redis_conn.blpop(_cron_enqueue_key(cron_job_id), timeout=timeout_seconds)  # type: ignore[assignment]
    if result is None:
        raise RuntimeError(f"Timed out waiting for cron enqueue event for {cron_job_id}")

    _, rq_job_id = result
    if decoded_job_id := _decode_redis_string(rq_job_id):
        return decoded_job_id
    raise RuntimeError(f"Received empty cron enqueue payload for {cron_job_id}")


@dataclass(frozen=True)
class RqE2EHarness:
    core_client: CoreRequestClient
    redis_backend: RedisBackend

    def queue(self, name: str) -> Queue:
        return Queue(name, connection=_redis_conn(self.redis_backend))

    def create(self, path: str, payload: JsonDict, resource_label: str) -> Any:
        response_payload = self.core_client.json_request("POST", path, json_data=payload)
        assert isinstance(response_payload, dict), f"Expected {resource_label} create response to be a dict"
        resource_id = response_payload.get("id")
        assert resource_id, f"{resource_label} id missing"
        return resource_id

    def create_wordlist(
        self,
        *,
        name: str,
        link: str,
        usage: int,
        description: str = "E2E",
    ) -> int:
        return self.create(
            "/config/word-lists",
            {"name": name, "description": description, "usage": usage, "link": link},
            "wordlist",
        )

    def gather_wordlist(self, wordlist_id: int) -> JsonDict:
        gather_job_id = f"gather_word_list_{wordlist_id}"
        previous_result_id = _get_latest_result_marker(self.redis_backend, gather_job_id)
        self.core_client.post(f"/config/word-lists/gather/{wordlist_id}")
        _wait_for_next_job_result(self.redis_backend, gather_job_id, previous_result_id)
        wordlist = self.core_client.json_request("GET", f"/config/word-lists/{wordlist_id}")
        assert isinstance(wordlist, dict), f"Expected wordlist payload to be a dict, got {type(wordlist)!r}"
        return wordlist

    def create_osint_source(self, payload: JsonDict) -> int:
        return self.create("/config/osint-sources", payload, "osint source")

    def update_osint_source(self, source_id: int, payload: JsonDict) -> JsonDict:
        response_payload = self.core_client.json_request("PUT", f"/config/osint-sources/{source_id}", json_data=payload)
        assert isinstance(response_payload, dict), "Expected osint source update response to be a dict"
        return response_payload

    def create_bot(self, payload: JsonDict) -> int:
        return self.create("/config/bots", payload, "bot")

    def update_bot(self, bot_id: int, payload: JsonDict) -> JsonDict:
        response_payload = self.core_client.json_request("PUT", f"/config/bots/{bot_id}", json_data=payload)
        assert isinstance(response_payload, dict), "Expected bot update response to be a dict"
        return response_payload

    def create_news_item(self, payload: JsonDict) -> JsonDict:
        response_payload = self.core_client.json_request("POST", "/assess/news-items", json_data=payload)
        assert isinstance(response_payload, dict), "Expected news item create response to be a dict"
        return response_payload

    def task_result(self, task_id: str) -> JsonDict:
        task_result = self.core_client.json_request("GET", f"/tasks/{task_id}")
        assert isinstance(task_result, dict), f"Expected task result to be a dict, got {type(task_result)!r}"
        return task_result

    def wait_for_job_result(self, job_id: str, timeout_seconds: int = DEFAULT_JOB_TIMEOUT_SECONDS) -> Result:
        return _wait_for_job_result(self.redis_backend, job_id, timeout_seconds=timeout_seconds)

    def assert_cron_registration(
        self,
        job_id: str,
        expected_cron: str | None = None,
    ) -> tuple[dict[str, Any], float]:
        return _assert_cron_registration(self.redis_backend, job_id, expected_cron=expected_cron)

    def wait_for_cron_task_result(
        self,
        cron_job_id: str,
        timeout_seconds: int = CRON_JOB_TIMEOUT_SECONDS,
    ) -> tuple[str, JsonDict]:
        run_job_id = _wait_for_cron_enqueue_event(self.redis_backend, cron_job_id, timeout_seconds=timeout_seconds)
        self.wait_for_job_result(run_job_id, timeout_seconds=timeout_seconds)
        return run_job_id, self.task_result(run_job_id)


@pytest.fixture
def rq_harness(
    core_request_client: CoreRequestClient,
    redis_backend: RedisBackend,
) -> RqE2EHarness:
    return RqE2EHarness(core_client=core_request_client, redis_backend=redis_backend)


@pytest.mark.e2e_ci
def test_rq_wordlist_queue_flow(
    worker_process: None,
    rq_harness: RqE2EHarness,
    wordlist_server: str,
) -> None:
    wordlist_id = rq_harness.create_wordlist(name="E2E Wordlist", link=wordlist_server, usage=0)
    payload = rq_harness.gather_wordlist(wordlist_id)
    assert (payload.get("entry_count") or 0) > 0


@pytest.mark.e2e_ci
def test_rq_cleanup_token_blacklist(
    worker_process: None,
    rq_harness: RqE2EHarness,
) -> None:
    queue = rq_harness.queue("misc")
    job_id = f"e2e_cleanup_token_blacklist_{int(time.time())}"

    queue.enqueue("worker.misc.misc_tasks.cleanup_token_blacklist", job_id=job_id)

    rq_harness.wait_for_job_result(job_id)
    payload = rq_harness.task_result(job_id)
    assert payload.get("status") == "SUCCESS"


@pytest.mark.e2e_ci
def test_rq_scheduled_collector_cron(
    worker_process: None,
    cron_process: None,
    rq_harness: RqE2EHarness,
    rss_server: str,
) -> None:
    cron_expression = "*/1 * * * *"
    source_payload = {
        "name": "E2E RSS Source",
        "description": "E2E RSS source for scheduled collector test",
        "type": "RSS_COLLECTOR",
        "parameters": {
            "FEED_URL": rss_server,
            "REFRESH_INTERVAL": cron_expression,
        },
    }
    source_id = rq_harness.create_osint_source(source_payload)
    cron_job_id = f"osint_source_{source_id}"
    rq_harness.assert_cron_registration(cron_job_id, expected_cron=cron_expression)

    _, payload = rq_harness.wait_for_cron_task_result(cron_job_id)
    assert payload.get("status") == "SUCCESS"
    assert source_payload["name"] in (payload.get("result") or "")


@pytest.mark.e2e_ci
def test_rq_osint_cron_update_immediately_refreshes_next_run(
    cron_process: None,
    rq_harness: RqE2EHarness,
    rss_server: str,
) -> None:
    initial_cron = "0 0 1 1 *"
    updated_cron = "*/1 * * * *"

    create_payload = {
        "name": "E2E Cron Reload Source",
        "description": "E2E source for cron update reload behavior",
        "type": "RSS_COLLECTOR",
        "parameters": {
            "FEED_URL": rss_server,
            "REFRESH_INTERVAL": initial_cron,
        },
    }
    source_id = rq_harness.create_osint_source(create_payload)
    job_id = f"osint_source_{source_id}"

    registered_spec, initial_next = rq_harness.assert_cron_registration(job_id, expected_cron=initial_cron)
    assert registered_spec.get("cron") == initial_cron

    update_payload = {"parameters": {"REFRESH_INTERVAL": updated_cron}}
    rq_harness.update_osint_source(source_id, update_payload)

    updated_spec, next_after_update = rq_harness.assert_cron_registration(job_id, expected_cron=updated_cron)
    assert updated_spec.get("cron") == updated_cron
    assert next_after_update != initial_next, "Expected scheduler to immediately recompute rq:cron:next after cron spec update"


@pytest.mark.e2e_ci
def test_rq_scheduled_wordlist_bot_cron(
    worker_process: None,
    cron_process: None,
    rq_harness: RqE2EHarness,
    wordlist_server: str,
) -> None:
    story_suffix = uuid.uuid4().hex

    rq_harness.create_news_item(
        {
            "title": f"E2E Story with alpha {story_suffix}",
            "source": "e2e",
            "content": "This story contains alpha to be tagged.",
            "review": "",
            "author": "e2e",
            "link": f"http://example.local/story/{story_suffix}",
            "language": "en",
            "published": "2026-02-09T12:00:00",
            "collected": "2026-02-09T12:00:00",
        }
    )
    wordlist_id = rq_harness.create_wordlist(name="E2E Tagging Wordlist", link=wordlist_server, usage=4)
    payload = rq_harness.gather_wordlist(wordlist_id)
    assert (payload.get("entry_count") or 0) > 0

    cron_expression = "*/1 * * * *"
    bot_payload = {
        "name": "E2E Wordlist Bot",
        "description": "E2E wordlist bot",
        "type": "WORDLIST_BOT",
        "parameters": {
            "REFRESH_INTERVAL": cron_expression,
        },
    }
    bot_id = rq_harness.create_bot(bot_payload)
    rq_harness.update_bot(bot_id, bot_payload)
    cron_job_id = f"bot_{bot_id}"
    rq_harness.assert_cron_registration(cron_job_id, expected_cron=cron_expression)

    _, payload = rq_harness.wait_for_cron_task_result(cron_job_id)
    assert payload.get("status") == "SUCCESS"
    assert payload.get("task") == f"bot_{bot_id}"
