import html
from datetime import UTC, datetime
from urllib.parse import urlparse

from models.assess import NewsItem

from worker.collectors.base_collector import BaseCollector
from worker.collectors.social_media import collect_image, publish_contribution, reddit_errors
from worker.http_client import http_request


class RedditCollector(BaseCollector):
    """Poll subreddit listings and recheck stored fullnames against the approved API."""

    def __init__(self):
        super().__init__()
        self.type = "REDDIT_COLLECTOR"
        self.name = "Reddit Collector"
        self.headers: dict[str, str] = {}

    def _connect(self, parameters):
        self.headers = {"User-Agent": parameters["USER_AGENT"]}
        with http_request(
            "POST",
            "https://www.reddit.com/api/v1/access_token",
            external=True,
            redirects=False,
            headers=self.headers,
            auth=(parameters["CLIENT_ID"], parameters["CLIENT_SECRET"]),
            data={"grant_type": "client_credentials"},
        ) as response:
            if response.status_code != 200:
                raise ValueError("Reddit authorization failed")
            self.headers["Authorization"] = f"Bearer {response.json()['access_token']}"

    def _listing(self, path, params):
        with http_request(
            "GET", f"https://oauth.reddit.com/{path}", external=True, redirects=False, headers=self.headers, params=params
        ) as response:
            if response.status_code != 200:
                raise ValueError("Reddit listing unavailable")
            return [row["data"] for row in response.json()["data"]["children"]]

    @staticmethod
    def _post(row) -> dict:
        key = row["name"]
        body = row.get("body", row.get("selftext", ""))
        if row.get("removed_by_category") or body in ("[removed]", "[deleted]"):
            return {"removed": key}
        images = []
        hosts = {"i.redd.it", "preview.redd.it"}
        if row.get("is_gallery"):
            for entry in row.get("gallery_data", {}).get("items", []):
                image_key = entry["media_id"]
                asset = row.get("media_metadata", {}).get(image_key, {})
                if asset.get("e") == "Image":
                    url = html.unescape(asset.get("s", {}).get("u", ""))
                    images.append(collect_image(image_key, url, entry.get("caption", ""), hosts))
        elif urlparse(row.get("url", "")).hostname == "i.redd.it":
            images.append(collect_image(key, row["url"], "", hosts))
        return {
            "key": key,
            "thread": row.get("link_id", key),
            "parent": row.get("parent_id") or "",
            "author": "" if row.get("author") == "[deleted]" else row.get("author") or "",
            "title": row.get("title", ""),
            "body": body,
            "url": "https://www.reddit.com" + row["permalink"],
            "published": datetime.fromtimestamp(row["created_utc"], UTC).isoformat(),
            "images": images,
            "warning": "Sensitive content" if row.get("over_18") or row.get("spoiler") else "",
        }

    @reddit_errors()
    def collect(self, source, manual=False):
        parameters = source["parameters"]
        self._connect(parameters)
        endpoint = f"/worker/social/{source['id']}"
        while True:
            due = self.core_api.api_get(endpoint)
            if due is None:
                raise ValueError("Could not load stored Reddit contributions")
            keys = set(due["keys"])
            if not keys:
                break
            refreshed = {r["name"]: r for r in self._listing("api/info", {"id": ",".join(sorted(keys))})}
            for key in sorted(keys):
                update = self._post(refreshed[key]) if key in refreshed else {"removed": key}
                if not publish_contribution(self.core_api, endpoint, update):
                    raise ValueError("Could not refresh a stored Reddit contribution")
            if len(keys) < 100:
                break
        found = {}
        for listing in ("new", "comments"):
            for row in self._listing(f"r/{parameters['SUBREDDIT']}/{listing}", {"limit": 100}):
                found[row["name"]] = row
        roots = {row["link_id"] for row in found.values() if row.get("link_id")} - found.keys()
        for start in range(0, len(roots), 100):
            found.update({row["name"]: row for row in self._listing("api/info", {"id": ",".join(sorted(roots)[start : start + 100])})})
        for row in found.values():
            if not publish_contribution(self.core_api, endpoint, self._post(row)):
                raise ValueError("Could not store a Reddit contribution")
        return "Social monitor updated"

    @reddit_errors()
    def preview_collector(self, source):
        self._connect(source["parameters"])
        rows = self._listing(f"r/{source['parameters']['SUBREDDIT']}/new", {"limit": 10})
        # Task history retains previews. Keep source-owned content in the monitor.
        return self.preview([NewsItem(osint_source_id=source["id"], title=f"{len(rows)} recent submissions available")], source)
