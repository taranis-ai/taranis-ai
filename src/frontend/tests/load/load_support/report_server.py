from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


class NoCacheRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        for header, value in NO_CACHE_HEADERS.items():
            self.send_header(header, value)
        super().end_headers()


def build_handler(directory: Path):
    return partial(NoCacheRequestHandler, directory=str(directory))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve load-test artifacts with cache disabled.")
    parser.add_argument("port", type=int)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--directory", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    directory = Path(args.directory).resolve()
    server = ThreadingHTTPServer((args.bind, args.port), build_handler(directory))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
