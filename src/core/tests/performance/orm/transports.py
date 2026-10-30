"""Local provider responses preserve Core parsing and persistence without network traffic."""

import io
import json

import requests


def chat_response(request, **kwargs):
    if not request.url.startswith("http://fixture.invalid/"):
        raise RuntimeError("An external request has no profiling transport fixture")
    payload = json.loads(request.body)
    messages = payload["messages"]
    searching = any("Profile search" in str(message.get("content", "")) for message in messages)
    answered_tool = any(message.get("role") == "tool" for message in messages)
    if searching and not answered_tool:
        delta = {
            "tool_calls": [
                {"index": 0, "id": "profile-search", "type": "function", "function": {"name": "search_stories", "arguments": "{}"}}
            ]
        }
        reason = "tool_calls"
    else:
        delta, reason = {"content": "Profile answer"}, "stop"
    events = [
        {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
        {"choices": [{"index": 0, "delta": {}, "finish_reason": reason}]},
    ]
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "text/event-stream"
    response.raw = io.BytesIO(("".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n").encode())
    response.request = request
    return response
