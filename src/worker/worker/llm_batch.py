"""OpenRouter batches resume the same RQ job without occupying a worker while waiting."""

import hashlib
import json
import time
from collections import defaultdict
from typing import Any
from urllib.parse import quote

from llm_bot.client import LLMClient
from niquests.exceptions import RequestException

from worker.http_client import http_request
from worker.log import logger


class BatchPending(Exception):
    def __init__(self, client: "BatchLLMClient"):
        super().__init__("LLM batch is pending")
        self.client = client


class BatchExecutionError(RuntimeError):
    public_message = "LLM batch failed. Check the batch status and model support at the provider."
    reason = "llm_batch_failed"
    retryable = False

    def __init__(self):
        super().__init__(self.public_message)


class BatchLLMClient(LLMClient):
    def __init__(self, *, state: dict, **kwargs: Any):
        super().__init__(**kwargs)
        self.state = state
        self.pending: dict[str, dict] = {}
        self.state.setdefault("batches", [])
        self.state.setdefault("responses", {})

    def request_batch(self, method: str, path: str = "", **kwargs: Any) -> dict:
        response = http_request(
            method, f"{self.base_url}/batches{path}", headers=self._headers(), timeout=self.timeout, verify=True, **kwargs
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("error"):
            raise BatchExecutionError
        return data

    def poll(self) -> None:
        for batch in self.state["batches"]:
            if batch.get("completed"):
                continue
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
                raise BatchPending(self) from None
            status = data.get("status")
            if status in {"validating", "in_progress", "finalizing", "cancelling"}:
                raise BatchPending(self)
            if status != "completed" or not isinstance(data.get("results"), list):
                raise BatchExecutionError
            responses = {}
            for result in data["results"]:
                custom_id = result.get("custom_id")
                response = result.get("response") or {}
                body = response.get("body")
                if (
                    custom_id not in batch["request_ids"]
                    or custom_id in responses
                    or result.get("error")
                    or response.get("status_code") != 200
                    or not isinstance(body, dict)
                    or body.get("error")
                ):
                    raise BatchExecutionError
                responses[custom_id] = body
            if set(responses) != set(batch["request_ids"]):
                raise BatchExecutionError
            self.state["responses"].update(responses)
            batch["completed"] = True

    def submit(self, save_state) -> None:
        # Separate schemas also work with Google's one-schema-per-batch constraint.
        groups = defaultdict(list)
        for custom_id, body in self.pending.items():
            schema = body.get("response_format", body.get("text", {}).get("format"))
            groups[json.dumps(schema, sort_keys=True)].append({"custom_id": custom_id, "body": body})
        for requests in groups.values():
            batch: dict[str, Any] = {"submitted_at": time.time(), "request_ids": [item["custom_id"] for item in requests]}
            self.state["batches"].append(batch)
            # A lost submission response must not cause a second paid submission on restart.
            save_state()
            path = "/v1/chat/completions" if self.api_mode == "chat_completions" else "/v1/responses"
            try:
                data = self.request_batch("POST", json={"endpoint": path, "model": self.model, "requests": requests})
            except RequestException:
                logger.exception("LLM batch submission failed")
                raise BatchExecutionError from None
            if not isinstance(data.get("id"), str) or not data["id"]:
                raise BatchExecutionError
            batch["id"] = data["id"]
            save_state()
        self.pending.clear()

    async def create_response(self, system_input: str, user_input: str, response_format: dict[str, Any] | None = None) -> dict[str, Any]:
        _, body = self._request_target(system_input, user_input, response_format)
        custom_id = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if custom_id in self.state["responses"]:
            response = self.state["responses"][custom_id]
            return self._normalize_chat_completions_response(response) if self.api_mode == "chat_completions" else response
        self.pending[custom_id] = body
        raise BatchPending(self)
