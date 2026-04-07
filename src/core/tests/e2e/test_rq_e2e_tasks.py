import json
import time
import uuid

import pytest
import redis
import requests
from rq import Queue


def _login(core_url: str) -> str:
    response = requests.post(
        f"{core_url}/auth/login",
        json={"username": "admin", "password": "admin"},
        timeout=5,
    )
    response.raise_for_status()
    if token := response.json().get("access_token"):
        return token
    else:
        raise RuntimeError("No access_token in auth response")


def _poll_wordlist_entries(
    core_url: str,
    headers: dict[str, str],
    wordlist_id: int,
    timeout_seconds: int = 30,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/word-lists/{wordlist_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            if (last_payload.get("entry_count") or 0) > 0:
                return last_payload
        time.sleep(0.5)
    raise RuntimeError(f"Word list did not update within {timeout_seconds}s. Last payload: {last_payload}")


def _poll_task_result(
    core_url: str,
    headers: dict[str, str],
    task_id: str,
    timeout_seconds: int = 30,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/task-results/{task_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            if last_payload.get("status") == "SUCCESS":
                return last_payload
        time.sleep(0.5)
    raise RuntimeError(f"Task {task_id} did not report SUCCESS within {timeout_seconds}s. Last payload: {last_payload}")


def _poll_cron_registration(
    redis_backend: dict[str, str],
    job_id: str,
    timeout_seconds: int = 15,
) -> dict:
    """Wait until a cron spec and its next run timestamp are registered in Redis."""
    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
    deadline = time.monotonic() + timeout_seconds
    last_raw_spec = None
    last_next = None

    while time.monotonic() < deadline:
        last_raw_spec = redis_conn.hget("rq:cron:def", job_id)
        last_next = redis_conn.zscore("rq:cron:next", job_id)
        if last_raw_spec and last_next is not None:
            parsed = json.loads(last_raw_spec.decode() if isinstance(last_raw_spec, bytes) else last_raw_spec)
            return parsed
        time.sleep(0.5)

    raise RuntimeError(f"Cron job {job_id} was not registered in Redis within {timeout_seconds}s. spec={last_raw_spec!r}, next={last_next!r}")


def _poll_cron_expression(
    redis_backend: dict[str, str],
    job_id: str,
    expected_cron: str,
    timeout_seconds: int = 10,
) -> dict:
    """Wait until a cron spec is present in Redis with the expected cron expression."""
    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
    deadline = time.monotonic() + timeout_seconds
    last_spec = None

    while time.monotonic() < deadline:
        raw_spec = redis_conn.hget("rq:cron:def", job_id)
        if raw_spec:
            parsed = json.loads(raw_spec.decode() if isinstance(raw_spec, bytes) else raw_spec)
            last_spec = parsed
            if parsed.get("cron") == expected_cron:
                return parsed
        time.sleep(0.5)

    raise RuntimeError(f"Cron spec for {job_id} did not update to {expected_cron!r} within {timeout_seconds}s. last_spec={last_spec!r}")


def _poll_collector_task_result(
    core_url: str,
    headers: dict[str, str],
    source_name: str,
    redis_backend: dict[str, str] | None = None,
    cron_job_id: str | None = None,
    timeout_seconds: int = 90,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/task-results", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            items = last_payload.get("items") if isinstance(last_payload, dict) else None
            if isinstance(items, list):
                for item in items:
                    if item.get("task") == "collector_task" and source_name in (item.get("result") or ""):
                        if item.get("status") == "SUCCESS":
                            return item
        time.sleep(1.0)
    details = ""
    if redis_backend and cron_job_id:
        redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
        next_run = redis_conn.zscore("rq:cron:next", cron_job_id)
        spec_exists = redis_conn.hexists("rq:cron:def", cron_job_id)
        queued = redis_conn.llen("rq:queue:collectors")
        failed = redis_conn.zcard("rq:failed:collectors")
        details = f" Redis spec_exists={spec_exists}, next={next_run!r}, queue_len={queued}, failed_len={failed}."
    raise RuntimeError(
        f"Collector task for source '{source_name}' did not report SUCCESS within {timeout_seconds}s. Last payload: {last_payload}.{details}"
    )


def _poll_bot_task_result(
    core_url: str,
    headers: dict[str, str],
    bot_task_name: str,
    redis_backend: dict[str, str] | None = None,
    cron_job_id: str | None = None,
    timeout_seconds: int = 90,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_payload = {}
    while time.monotonic() < deadline:
        resp = requests.get(f"{core_url}/config/task-results", headers=headers, timeout=5)
        if resp.status_code == 200:
            last_payload = resp.json()
            items = last_payload.get("items") if isinstance(last_payload, dict) else None
            if isinstance(items, list):
                for item in items:
                    if item.get("task") == bot_task_name and item.get("status") == "SUCCESS":
                        return item
        time.sleep(1.0)
    details = ""
    if redis_backend and cron_job_id:
        redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
        next_run = redis_conn.zscore("rq:cron:next", cron_job_id)
        spec_exists = redis_conn.hexists("rq:cron:def", cron_job_id)
        queued = redis_conn.llen("rq:queue:bots")
        failed = redis_conn.zcard("rq:failed:bots")
        details = f" Redis spec_exists={spec_exists}, next={next_run!r}, queue_len={queued}, failed_len={failed}."
    raise RuntimeError(f"Bot task '{bot_task_name}' did not report SUCCESS within {timeout_seconds}s. Last payload: {last_payload}.{details}")


@pytest.mark.e2e_ci
def test_rq_wordlist_queue_flow(
    core_process: str,
    worker_process: None,
    wordlist_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

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

    payload = _poll_wordlist_entries(core_process, headers, wordlist_id)
    assert (payload.get("entry_count") or 0) > 0


@pytest.mark.e2e_ci
def test_rq_cleanup_token_blacklist(
    core_process: str,
    worker_process: None,
    redis_backend: dict[str, str],
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
    # Use explicit queue name to match worker configuration.
    queue = Queue("misc", connection=redis_conn)
    job_id = f"e2e_cleanup_token_blacklist_{int(time.time())}"

    queue.enqueue("worker.misc.misc_tasks.cleanup_token_blacklist", job_id=job_id)

    payload = _poll_task_result(core_process, headers, job_id, timeout_seconds=30)
    assert payload.get("status") == "SUCCESS"


@pytest.mark.e2e_ci
def test_rq_scheduled_collector_cron(
    core_process: str,
    worker_process: None,
    cron_process: None,
    redis_backend: dict[str, str],
    rss_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

    # Create a minimal RSS collector source using the local feed server.
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
    _poll_cron_registration(redis_backend, f"osint_source_{source_id}")

    # Use cron schedule (every minute) and wait for scheduler + worker to execute it.
    payload = _poll_collector_task_result(
        core_process,
        headers,
        source_payload["name"],
        redis_backend=redis_backend,
        cron_job_id=f"osint_source_{source_id}",
        timeout_seconds=90,
    )
    assert payload.get("status") == "SUCCESS"


@pytest.mark.e2e_ci
def test_rq_osint_cron_update_immediately_refreshes_next_run(
    core_process: str,
    cron_process: None,
    redis_backend: dict[str, str],
    rss_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}

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

    registered_spec = _poll_cron_registration(redis_backend, job_id)
    assert registered_spec.get("cron") == initial_cron

    redis_conn = redis.from_url(redis_backend["url"], password=redis_backend["password"] or None, decode_responses=False)
    initial_next = redis_conn.zscore("rq:cron:next", job_id)
    assert initial_next is not None

    update_payload = {"parameters": {"REFRESH_INTERVAL": updated_cron}}
    update_resp = requests.put(
        f"{core_process}/config/osint-sources/{source_id}",
        headers=headers,
        json=update_payload,
        timeout=5,
    )
    update_resp.raise_for_status()

    updated_spec = _poll_cron_expression(redis_backend, job_id, updated_cron)
    assert updated_spec.get("cron") == updated_cron

    deadline = time.monotonic() + 4.0
    next_after_update = redis_conn.zscore("rq:cron:next", job_id)
    while time.monotonic() < deadline and next_after_update == initial_next:
        time.sleep(0.5)
        next_after_update = redis_conn.zscore("rq:cron:next", job_id)

    assert next_after_update is not None
    assert next_after_update != initial_next, "Expected scheduler to immediately recompute rq:cron:next after cron spec update"


@pytest.mark.e2e_ci
def test_rq_scheduled_wordlist_bot_cron(
    core_process: str,
    worker_process: None,
    cron_process: None,
    redis_backend: dict[str, str],
    wordlist_server: str,
) -> None:
    token = _login(core_process)
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
    story_suffix = uuid.uuid4().hex

    # Ensure a story exists with a matching word for the bot to tag.
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

    # Create a word list used by the tagging bot and populate it.
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
    _poll_wordlist_entries(core_process, headers, wordlist_id)

    # Create a Wordlist Bot with a cron schedule and trigger cron reload via update.
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
    _poll_cron_registration(redis_backend, f"bot_{bot_id}")

    payload = _poll_bot_task_result(
        core_process,
        headers,
        f"bot_{bot_id}",
        redis_backend=redis_backend,
        cron_job_id=f"bot_{bot_id}",
        timeout_seconds=90,
    )
    assert payload.get("status") == "SUCCESS"
