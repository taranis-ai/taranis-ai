"""Fetch article-controlled image URLs without forwarding source credentials."""

import ipaddress
import socket
import time
from urllib.parse import urldefrag, urlencode, urljoin, urlsplit

import niquests
from bs4 import BeautifulSoup
from models.news_image import MAX_IMAGE_BYTES, MAX_IMAGE_COUNT
from niquests.utils import get_environ_proxies, select_proxy


def image_urls(markup: str) -> list[str]:
    soup = BeautifulSoup(markup, "lxml")
    return [str(node["src"]) for node in soup.select("img[src], graphic[src]", limit=MAX_IMAGE_COUNT)]


def resolve_candidates(base: str, urls: list[str]) -> list[str]:
    result = []
    for value in urls:
        try:
            url = urldefrag(urljoin(base, value.strip())).url
            if url not in result and urlsplit(url).scheme in {"http", "https"}:
                result.append(url)
        except ValueError:
            continue
        if len(result) == MAX_IMAGE_COUNT:
            break
    return result


def download_image(url: str, proxy_server: str | None = None) -> bytes:
    deadline = time.monotonic() + 15
    for _ in range(4):
        # Use the transport's canonical URL for both validation and the request.
        prepared = niquests.PreparedRequest()
        prepared.prepare_url(url, None)
        url = prepared.url or ""
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not host or parsed.username is not None or parsed.password is not None:
            raise ValueError("Invalid image URL")
        if proxy_server or select_proxy(url, get_environ_proxies(url)):
            # A remote proxy resolves the target independently of our validated addresses.
            raise ValueError("Image requests require direct public egress")
        addresses = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
        ips = [ipaddress.ip_address(entry[4][0]) for entry in addresses]
        if not ips or any(not ip.is_global or ip.is_multicast for ip in ips):
            raise ValueError("Image destination is not public")

        # Pin the validated address while keeping the original hostname for TLS and Host.
        resolver = "in-memory://default?" + urlencode({"hosts": f"{host}:{ips[0]}"})
        with niquests.Session(resolver=resolver, retries=0, disable_http3=True) as session:
            session.trust_env = False
            with session.get(url, headers={"Accept-Encoding": "identity"}, timeout=5, allow_redirects=False, stream=True) as response:
                if time.monotonic() >= deadline:
                    raise ValueError("Image download timed out")
                if response.is_redirect:
                    url = urljoin(url, str(response.headers["Location"]))
                    continue
                if response.status_code != 200 or response.headers.get("Content-Encoding", "identity") != "identity":
                    raise ValueError("Image download failed")
                data = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    if len(data) + len(chunk) > MAX_IMAGE_BYTES or time.monotonic() >= deadline:
                        raise ValueError("Image download exceeded its limit")
                    data.extend(chunk)
                return bytes(data)
    raise ValueError("Too many image redirects")
