"""Submit prepared tasks together and resume the RQ job when their results arrive."""

import json
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from llm_bot.client import LLMClient
from llm_bot.tasks.llm_utils import LLMTask
from niquests.exceptions import RequestException

from worker.http_client import http_request
from worker.log import logger


class BatchExecutionError(RuntimeError):
    public_message = "LLM batch failed. Check the batch status and model support at the provider."
    reason = "llm_batch_failed"
    retryable = False

    def __init__(self):
        super().__init__(self.public_message)


class BatchProcessor:
    def __init__(self, client: LLMClient, state: dict, save_state: Callable[[], None]):
        self.client = client
        self.state = state
        self.save_state = save_state

    def request_batch(self, method: str, path: str = "", **kwargs: Any) -> dict:
        response = http_request(
            method,
            f"{self.client.base_url}/batches{path}",
            headers={"Authorization": f"Bearer {self.client.api_key}"},
            timeout=self.client.timeout,
            verify=True,
            **kwargs,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("error"):
            raise BatchExecutionError
        return data

    def process[T](self, tasks: list[LLMTask[T]]) -> list[T] | None:
        if not tasks:
            return []
        if "batches" not in self.state:
            self.submit(tasks)
            return None
        responses = self.poll()
        if responses is None:
            return None
        if set(responses) != {str(index) for index in range(len(tasks))}:
            raise BatchExecutionError
        try:
            return [task.parse_result(responses[str(index)], self.client) for index, task in enumerate(tasks)]
        except Exception:
            logger.exception("Invalid LLM batch output")
            raise BatchExecutionError from None

    def submit(self, tasks: list[LLMTask]) -> None:
        # Google requires one output schema per batch; summary and title use different schemas.
        groups = defaultdict(list)
        for index, task in enumerate(tasks):
            body = task.build_request(self.client)
            schema = body.get("response_format", body.get("text", {}).get("format"))
            groups[json.dumps(schema, sort_keys=True)].append({"custom_id": str(index), "body": body})
        batches: list[dict[str, Any]] = [
            {"submitted_at": time.time(), "request_ids": [item["custom_id"] for item in requests]} for requests in groups.values()
        ]
        self.state["batches"] = batches
        # Save before POST: a lost submission response must not cause another paid submission.
        self.save_state()
        path = "/v1/chat/completions" if self.client.api_mode == "chat_completions" else "/v1/responses"
        for batch, requests in zip(batches, groups.values(), strict=True):
            try:
                data = self.request_batch("POST", json={"endpoint": path, "model": self.client.model, "requests": requests})
            except RequestException:
                logger.exception("LLM batch submission failed")
                raise BatchExecutionError from None
            if not isinstance(data.get("id"), str) or not data["id"]:
                raise BatchExecutionError
            batch["id"] = data["id"]
            self.save_state()

    def poll(self) -> dict[str, dict] | None:
        responses = {}
        pending = False
        for batch in self.state["batches"]:
            if not batch.get("id") or time.time() - batch["submitted_at"] > 25 * 3600:
                raise BatchExecutionError
            try:
                data = self.request_batch("GET", f"/{quote(batch['id'], safe='')}")
            except RequestException as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code is not None and 400 <= status_code < 500:
                    logger.exception("LLM batch status request was rejected")
                    raise BatchExecutionError from None
                logger.exception("Could not retrieve LLM batch; retrying the status check")
                pending = True
                continue
            status = data.get("status")
            if status in {"validating", "in_progress", "finalizing", "cancelling"}:
                pending = True
                continue
            if status != "completed" or not isinstance(data.get("results"), list):
                raise BatchExecutionError
            batch_responses = {}
            for result in data["results"]:
                if not isinstance(result, dict):
                    raise BatchExecutionError
                custom_id = result.get("custom_id")
                response = result.get("response") or {}
                if not isinstance(response, dict):
                    raise BatchExecutionError
                body = response.get("body")
                if (
                    not isinstance(custom_id, str)
                    or custom_id not in batch["request_ids"]
                    or custom_id in batch_responses
                    or result.get("error")
                    or response.get("status_code") != 200
                    or not isinstance(body, dict)
                    or body.get("error")
                ):
                    raise BatchExecutionError
                batch_responses[custom_id] = body
            if set(batch_responses) != set(batch["request_ids"]):
                raise BatchExecutionError
            responses.update(batch_responses)
        return None if pending else responses
