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
        if self.path == "/v1/decisions":
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            answers = []
            for question in payload["questions"]:
                name = question["name"]
                choice = "OK" if name == "probe" else ("not_stated" if " owns " in question["instructions"] else "affirmed")
                answers.append(
                    {
                        "type": "choice",
                        "name": name,
                        "choice": choice,
                        "probabilities": [
                            {"value": value, "probability": float(value == choice)}
                            for value in (["OK", "other"] if name == "probe" else ["affirmed", "negated", "uncertain", "not_stated"])
                        ],
                    }
                )
            self.send_json({"answers": answers})
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
        if schema_name == "entity_relationship_extraction_response":
            content = context["text"]
            entities = [{"id": "demo", "type": "ORG", "name": "Demo"}] if content.startswith("Demo") else []
            relations = []
            if content.startswith("Demo uses Example."):
                entities.append({"id": "example", "type": "PRODUCT", "name": "Example"})
                relations = [
                    {"source_id": "demo", "target_id": "example", "type": kind, "assertion": "uncertain", "quote": "Demo uses Example."}
                    for kind in ("USES", "OWNS")
                ]
            self.reply(
                [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps({"entities": entities, "relations": relations})}],
                    }
                ]
            )
            return
        if schema_name == "graph_query_generation_response":
            self.reply(
                [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps({"names": ["demo"], "hops": 1, "filters": {"search": "ransomware"}})}
                        ],
                    }
                ]
            )
            return
        if schema_name == "hrag_response":
            citations = [entry["id"] for entry in context["graph_facts"] + context["passages"]]
            result = {
                "answer": "Demo evidence: " + " ".join(f"[{citation}]" for citation in citations),
                "citations": citations,
                "insufficient_evidence": not citations,
            }
            self.reply([{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result)}]}])
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
        self.send_json({"status": "completed", "output": output})

    def send_json(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), DemoChatProvider).serve_forever()
