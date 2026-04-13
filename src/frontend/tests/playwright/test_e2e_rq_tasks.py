import json
import time
import uuid
from typing import Any

import pytest
import redis
import requests
from rq import Queue
from rq.job import Job
from rq.results import Result


CRON_ENQUEUE_KEY_PREFIX = "rq:cron:enqueue:"


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


def _redis_conn(redis_backend: dict[str, str]) -> redis.Redis:
    return redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)


def _decode_redis_string(raw_value: bytes | str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.decode() if isinstance(raw_value, bytes) else raw_value


def _cron_enqueue_key(job_id: str) -> str:
    return f"{CRON_ENQUEUE_KEY_PREFIX}{job_id}"


def _wait_for_job_result(
    redis_backend: dict[str, str],
    job_id: str,
    timeout_seconds: int = 30,
) -> Result:
    job = Job.fetch(job_id, connection=_redis_conn(redis_backend))
    result = job.latest_result(timeout=timeout_seconds)
    if result is None:
        raise RuntimeError(f"Timed out waiting for RQ result stream for job {job_id}")
    if result.type == Result.Type.FAILED:
        raise RuntimeError(f"Job {job_id} failed: {result.exc_string}")
    return result


def _get_task_result(
    core_url: str,
    headers: dict[str, str],
    task_id: str,
) -> dict:
    resp = requests.get(f"{core_url}/config/task-results/{task_id}", headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()


def _get_wordlist(
    core_url: str,
    headers: dict[str, str],
    wordlist_id: int,
) -> dict:
    resp = requests.get(f"{core_url}/config/word-lists/{wordlist_id}", headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()


def _assert_cron_registration(
    redis_backend: dict[str, str],
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
    redis_backend: dict[str, str],
    cron_job_id: str,
    timeout_seconds: int = 90,
) -> str:
    redis_conn = _redis_conn(redis_backend)
    result: tuple[bytes, bytes] | None = redis_conn.blpop(_cron_enqueue_key(cron_job_id), timeout=timeout_seconds)  # type: ignore[assignment]
    if result is None:
        raise RuntimeError(f"Timed out waiting for cron enqueue event for {cron_job_id}")

    _, rq_job_id = result
    if decoded_job_id := _decode_redis_string(rq_job_id):
        return decoded_job_id
    else:
        raise RuntimeError(f"Received empty cron enqueue payload for {cron_job_id}")


@pytest.mark.e2e_ci
def test_rq_wordlist_queue_flow(
    core_process: str,
    worker_process: None,
    redis_backend: dict[str, str],
    wordlist_server: str,
    access_token: str,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}

    create_resp = requests.post(
        f"{core_process}/config/word-lists",
        headers=headers,
        json={"name": "E2E Wordlist", "description": "E2E", "usage": 0, "link": wordlist_server},
        timeout=5,
    )
    create_resp.raise_for_status()
    wordlist_id = create_resp.json().get("id")
    assert wordlist_id, "wordlist id missing"

    enqueue_resp = requests.post(
        f"{core_process}/config/word-lists/gather/{wordlist_id}",
        headers=headers,
        timeout=5,
    )
    enqueue_resp.raise_for_status()

    _wait_for_job_result(redis_backend, f"gather_word_list_{wordlist_id}")
    payload = _get_wordlist(core_process, headers, wordlist_id)
    assert (payload.get("entry_count") or 0) > 0


@pytest.mark.e2e_ci
def test_rq_cleanup_token_blacklist(
    core_process: str,
    worker_process: None,
    redis_backend: dict[str, str],
    access_token: str,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}

    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
    queue = Queue("misc", connection=redis_conn)
    job_id = f"e2e_cleanup_token_blacklist_{int(time.time())}"

    queue.enqueue("worker.misc.misc_tasks.cleanup_token_blacklist", job_id=job_id)

    _wait_for_job_result(redis_backend, job_id, timeout_seconds=30)
    payload = _get_task_result(core_process, headers, job_id)
    assert payload.get("status") == "SUCCESS"


@pytest.mark.e2e_ci
def test_rq_scheduled_collector_cron(
    core_process: str,
    worker_process: None,
    cron_process: None,
    redis_backend: dict[str, str],
    rss_server: str,
    access_token: str,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}

    source_payload = {
        "name": "E2E RSS Source",
        "description": "E2E RSS source for scheduled collector test",
        "type": "RSS_COLLECTOR",
        "parameters": {
            "FEED_URL": rss_server,
            "REFRESH_INTERVAL": "*/1 * * * *",
        },
    }
    create_resp = requests.post(
        f"{core_process}/config/osint-sources",
        headers=headers,
        json=source_payload,
        timeout=5,
    )
    create_resp.raise_for_status()
    source_id = create_resp.json().get("id")
    assert source_id, "osint source id missing"
    cron_job_id = f"osint_source_{source_id}"
    _assert_cron_registration(redis_backend, cron_job_id, expected_cron=source_payload["parameters"]["REFRESH_INTERVAL"])

    run_job_id = _wait_for_cron_enqueue_event(redis_backend, cron_job_id, timeout_seconds=90)
    _wait_for_job_result(redis_backend, run_job_id, timeout_seconds=90)
    payload = _get_task_result(core_process, headers, run_job_id)
    assert payload.get("status") == "SUCCESS"
    assert source_payload["name"] in (payload.get("result") or "")


@pytest.mark.e2e_ci
def test_rq_osint_cron_update_immediately_refreshes_next_run(
    core_process: str,
    cron_process: None,
    redis_backend: dict[str, str],
    rss_server: str,
    access_token: str,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}

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
    create_resp = requests.post(
        f"{core_process}/config/osint-sources",
        headers=headers,
        json=create_payload,
        timeout=5,
    )
    create_resp.raise_for_status()
    source_id = create_resp.json().get("id")
    assert source_id, "osint source id missing"
    job_id = f"osint_source_{source_id}"

    registered_spec, initial_next = _assert_cron_registration(redis_backend, job_id, expected_cron=initial_cron)
    assert registered_spec.get("cron") == initial_cron

    update_payload = {"parameters": {"REFRESH_INTERVAL": updated_cron}}
    update_resp = requests.put(
        f"{core_process}/config/osint-sources/{source_id}",
        headers=headers,
        json=update_payload,
        timeout=5,
    )
    update_resp.raise_for_status()

    updated_spec, next_after_update = _assert_cron_registration(redis_backend, job_id, expected_cron=updated_cron)
    assert updated_spec.get("cron") == updated_cron
    assert next_after_update != initial_next, "Expected scheduler to immediately recompute rq:cron:next after cron spec update"


@pytest.mark.e2e_ci
def test_rq_scheduled_wordlist_bot_cron(
    core_process: str,
    worker_process: None,
    cron_process: None,
    redis_backend: dict[str, str],
    wordlist_server: str,
    access_token: str,
) -> None:
    headers = {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}
    story_suffix = uuid.uuid4().hex

    story_resp = requests.post(
        f"{core_process}/assess/news-items",
        headers=headers,
        json={
            "title": f"E2E Story with alpha {story_suffix}",
            "source": "e2e",
            "content": "This story contains alpha to be tagged.",
            "review": "",
            "author": "e2e",
            "link": f"http://example.local/story/{story_suffix}",
            "language": "en",
            "published": "2026-02-09T12:00:00",
            "collected": "2026-02-09T12:00:00",
        },
        timeout=5,
    )
    assert story_resp.ok, f"Failed to create manual story: status={story_resp.status_code}, body={story_resp.text}"

    wordlist_resp = requests.post(
        f"{core_process}/config/word-lists",
        headers=headers,
        json={"name": "E2E Tagging Wordlist", "description": "E2E", "usage": 4, "link": wordlist_server},
        timeout=5,
    )
    wordlist_resp.raise_for_status()
    wordlist_id = wordlist_resp.json().get("id")
    assert wordlist_id, "wordlist id missing"

    gather_resp = requests.post(
        f"{core_process}/config/word-lists/gather/{wordlist_id}",
        headers=headers,
        timeout=5,
    )
    gather_resp.raise_for_status()
    _wait_for_job_result(redis_backend, f"gather_word_list_{wordlist_id}")
    payload = _get_wordlist(core_process, headers, wordlist_id)
    assert (payload.get("entry_count") or 0) > 0

    bot_payload = {
        "name": "E2E Wordlist Bot",
        "description": "E2E wordlist bot",
        "type": "WORDLIST_BOT",
        "parameters": {
            "REFRESH_INTERVAL": "*/1 * * * *",
        },
    }
    bot_create = requests.post(
        f"{core_process}/config/bots",
        headers=headers,
        json=bot_payload,
        timeout=5,
    )
    bot_create.raise_for_status()
    bot_id = bot_create.json().get("id")
    assert bot_id, "bot id missing"

    bot_update = requests.put(
        f"{core_process}/config/bots/{bot_id}",
        headers=headers,
        json=bot_payload,
        timeout=5,
    )
    bot_update.raise_for_status()
    cron_job_id = f"bot_{bot_id}"
    _assert_cron_registration(redis_backend, cron_job_id, expected_cron=bot_payload["parameters"]["REFRESH_INTERVAL"])

    run_job_id = _wait_for_cron_enqueue_event(redis_backend, cron_job_id, timeout_seconds=90)
    _wait_for_job_result(redis_backend, run_job_id, timeout_seconds=90)
    payload = _get_task_result(core_process, headers, run_job_id)
    assert payload.get("status") == "SUCCESS"
    assert payload.get("task") == f"bot_{bot_id}"
