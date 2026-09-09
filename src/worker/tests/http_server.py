import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue
from typing import cast


class RecordingHTTPServer(ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), RecordingHTTPHandler)
        self.closed_connections: Queue[int] = Queue()
        self.received: list[tuple[str, str]] = []

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"


class RecordingHTTPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        server = cast(RecordingHTTPServer, self.server)
        server.received.append((self.command, self.path))
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        payload = json.dumps(
            {
                "port": self.client_address[1],
                "authorization": self.headers.get("Authorization"),
                "cookie": self.headers.get("Cookie"),
            }
        ).encode()
        self.send_response(307 if self.path == "/redirect" else 503 if self.path == "/unavailable" else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Set-Cookie", "upstream=secret; Path=/")
        if self.path == "/redirect":
            self.send_header("Location", "/echo")
        self.end_headers()
        self.wfile.write(payload)

    do_POST = do_GET

    def finish(self):
        try:
            super().finish()
        finally:
            cast(RecordingHTTPServer, self.server).closed_connections.put(self.client_address[1])

    def log_message(self, format, *args):
        pass
