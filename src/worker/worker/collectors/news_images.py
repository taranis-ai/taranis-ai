"""Fetch article-controlled image URLs without forwarding source credentials."""

import asyncio
import ipaddress
import socket
from collections.abc import Iterable
from urllib.parse import urldefrag, urlencode, urljoin, urlsplit

import niquests
from bs4 import BeautifulSoup
from models.news_image import MAX_IMAGE_BYTES, MAX_IMAGE_COUNT, normalize_alt_text
from niquests.utils import get_environ_proxies, select_proxy


IMAGE_TIMEOUT_SECONDS = 15


def document_base_url(markup: str, page_url: str) -> str:
    base = BeautifulSoup(markup, "lxml").select_one("base[href]")
    if base is not None:
        try:
            return urljoin(page_url, str(base["href"]))
        except ValueError:
            pass
    return page_url


def markup_images(markup: str) -> list[tuple[str, str | None]]:
    soup = BeautifulSoup(markup, "lxml")
    return [(str(node["src"]), str(node.get("alt") or "")) for node in soup.select("img[src], graphic[src]", limit=MAX_IMAGE_COUNT)]


def resolve_candidates(base: str, candidates: Iterable[tuple[str, str | None]]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for value, alt_text in candidates:
        try:
            url = urldefrag(urljoin(base, value.strip())).url
            if urlsplit(url).scheme not in {"http", "https"}:
                continue
        except ValueError:
            continue
        if url in result or len(result) < MAX_IMAGE_COUNT:
            result[url] = result.get(url) or normalize_alt_text(alt_text)
    return result


async def download_image(url: str, proxy_server: str | None = None) -> bytes:
    async with asyncio.timeout(IMAGE_TIMEOUT_SECONDS):
        for _ in range(4):
            # Use the transport's canonical URL for both validation and the request.
            prepared = niquests.Request("GET", url, headers={"Accept-Encoding": "identity"}).prepare()
            url = prepared.url or ""
            parsed = urlsplit(url)
            host = parsed.hostname
            if parsed.scheme not in {"http", "https"} or not host or parsed.username is not None or parsed.password is not None:
                raise ValueError("Invalid image URL")
            if proxy_server or select_proxy(url, get_environ_proxies(url)):
                # A remote proxy resolves the target independently of our validated addresses.
                raise ValueError("Image requests require direct public egress")
            addresses = await asyncio.get_running_loop().getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
            ips = [ipaddress.ip_address(entry[4][0]) for entry in addresses]
            if not ips or any(not ip.is_global or ip.is_multicast for ip in ips):
                raise ValueError("Image destination is not public")

            # Pin the validated address while keeping the original hostname for TLS and Host.
            resolver = "in-memory://default?" + urlencode({"hosts": f"{host}:{ips[0]}"})
            async with niquests.AsyncSession(resolver=resolver, retries=0, disable_http3=True) as session:
                # Send one hop directly: Session.get otherwise consumes redirect bodies to prepare Response.next.
                response = await session.get_adapter(url).send(prepared, timeout=5, stream=True)
                async with response:
                    if response.is_redirect:
                        url = urljoin(url, str(response.headers["Location"]))
                        continue
                    if response.status_code != 200 or response.headers.get("Content-Encoding", "identity") != "identity":
                        raise ValueError("Image download failed")
                    data = bytearray()
                    async for chunk in await response.iter_content(64 * 1024):
                        if len(data) + len(chunk) > MAX_IMAGE_BYTES:
                            raise ValueError("Image download exceeded its limit")
                        data.extend(chunk)
                    return bytes(data)
        raise ValueError("Too many image redirects")
