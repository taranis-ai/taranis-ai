"""Scripted Responses provider for the landing-page recording; never contacts an LLM."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class DemoChatProvider(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/v1/embeddings":
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            vector = [1, 0, 0] if "demo" in str(payload.get("input", "")).lower() else [0, 1, 0]
            body = json.dumps({"data": [{"embedding": vector}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if payload["input"] == "Reply with OK.":
            self.reply([{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "OK"}]}])
            return
        context = json.loads(next(item["content"] for item in payload["input"] if item.get("role") == "user"))
        schema_name = payload.get("text", {}).get("format", {}).get("name")
        if schema_name == "evidence_extraction":
            content = context["text"]
            entities = (
                [{"id": "demo", "type": "ORG", "name": "Demo", "evidence": {"start": 0, "end": 4, "quote": "Demo"}}]
                if content.startswith("Demo")
                else []
            )
            self.reply(
                [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({"entities": entities, "relations": []})}]}]
            )
            return
        if schema_name == "retrieval_plan":
            self.reply(
                [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps({"names": ["demo"], "hops": 0, "filters": {"search": "ransomware"}})}
                        ],
                    }
                ]
            )
            return
        if "retrieval" in context:
            evidence = context["retrieval"]["evidence"]
            answer = "Demo evidence: " + " ".join(f"[{entry['citation']}]" for entry in evidence)
            self.reply([{"type": "message", "content": [{"type": "output_text", "text": answer}]}])
            return
        unread = "unread" in context["latest_message"].lower()
        if payload.get("tools"):
            filters = {"search": "ransomware"}
            if unread:
                filters["read"] = False
            output = [{"type": "function_call", "name": "search_stories", "call_id": "demo-search", "arguments": json.dumps(filters)}]
        else:
            result = json.loads(payload["input"][-1]["output"])
            label = "unread ransomware" if unread else "ransomware"
            titles = "\n".join(f"• {story['title']}" for story in result["stories"])
            answer = (
                f"I found {result['total_count']} {label} stories in your collection.\n\n"
                f"Here are the matching headlines:\n{titles}\n\n"
                "Open the matching stories in Assess to review the sources and continue your analysis."
            )
            output = [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": answer}]}]
        self.reply(output)

    def reply(self, output):
        body = json.dumps({"status": "completed", "output": output}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), DemoChatProvider).serve_forever()
