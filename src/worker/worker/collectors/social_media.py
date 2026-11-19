import base64
from contextlib import contextmanager
from urllib.parse import urlparse

from niquests.exceptions import RequestException

from worker.http_client import http_request
from worker.log import logger


class SocialCollectorError(Exception):
    def __init__(self, public_message: str, reason: str):
        super().__init__(public_message)
        self.public_message = public_message
        self.reason = reason


@contextmanager
def reddit_errors():
    try:
        yield
    except Exception as error:
        logger.exception("Reddit API or collection request failed")
        raise SocialCollectorError(
            "Could not collect from Reddit. Check application access and rate limits.", "reddit_collection_failed"
        ) from error


def collect_image(key: str, url: str, alt: str, hosts: set[str], proxy: str | None = None) -> dict:
    """Only download raster attachments from configured platform hosts, without credentials."""
    result = {"key": key, "alt": alt or ""}
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return result
    if parsed.scheme != "https" or parsed.hostname not in hosts or parsed.username or parsed.password or port not in (443, None):
        return result
    limit = 12 * 1024 * 1024
    try:
        with http_request("GET", url, external=True, redirects=False, stream=True, proxies={"https": proxy} if proxy else None) as response:
            if response.status_code != 200 or int(response.headers.get("Content-Length") or 0) > limit:
                return result
            data = bytearray()
            for chunk in response.iter_content(65536):
                if len(data) + len(chunk) > limit:
                    return result
                data.extend(chunk)
            if data:
                result["data"] = base64.b64encode(data).decode("ascii")
    except (RequestException, ValueError):
        logger.warning("Social image download unavailable")
    return result


def publish_contribution(api, endpoint, post):
    """Send large galleries one image at a time within the ingress request limit."""
    images = post.get("images", [])
    if sum(len(image.get("data", "")) for image in images) < 32 * 1024 * 1024:
        return api.api_post(endpoint, post)
    metadata = {**post, "images": [{k: v for k, v in image.items() if k != "data"} for image in images]}
    result = api.api_post(endpoint, metadata)
    if not result:
        return None
    for image in images:
        if image.get("data") and not api.api_post(f"{endpoint}/{result['id']}/image", image):
            return None
    return result
