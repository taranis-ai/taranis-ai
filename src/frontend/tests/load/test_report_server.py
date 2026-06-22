from __future__ import annotations

import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from tests.load.load_support.report_server import NO_CACHE_HEADERS, build_handler


def test_report_server_disables_browser_caching(tmp_path: Path) -> None:
    report_path = tmp_path / "locust-report.html"
    report_path.write_text("<html>report</html>", encoding="utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/locust-report.html") as response:
            headers = response.headers
            body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert body == "<html>report</html>"
    for header, value in NO_CACHE_HEADERS.items():
        assert headers[header] == value
