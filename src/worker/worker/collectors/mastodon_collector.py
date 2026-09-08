from typing import Any

from bs4 import BeautifulSoup
from mastodon import Mastodon
from mastodon.errors import (
    MastodonAPIError,
    MastodonError,
    MastodonNetworkError,
    MastodonNotFoundError,
    MastodonRatelimitError,
    MastodonUnauthorizedError,
)
from models.assess import NewsItem

from worker.collectors.base_collector import BaseCollector, NoChangeError
from worker.log import logger


MASTODON_PAGE_SIZE = 40
MASTODON_SKIP_MESSAGE = "Mastodon latest mode skipped older statuses to stay current; use complete mode to prevent gaps"


class MastodonCollectorError(Exception):
    def __init__(self, public_message: str, reason: str):
        super().__init__(public_message)
        self.public_message = public_message
        self.reason = reason


class MastodonCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "MASTODON_COLLECTOR"
        self.name = "Mastodon Collector"
        self.description = "Collector for gathering statuses from Mastodon timelines"
        self.client: Mastodon | None = None
        self.instance_url = ""
        self.timeline = ""
        self.target = ""
        self.collection_mode = "complete"
        self.has_access_token = False
        self.mastodon_cursor: dict[str, str] | None = None
        self.skipped_statuses = False

    @staticmethod
    def _plain_text(value: Any) -> str:
        return BeautifulSoup(str(value or ""), "lxml").get_text(" ", strip=True)

    @staticmethod
    def _status_id(status: Any) -> str:
        status_id = status["id"]
        if status_id is None or not str(status_id):
            raise ValueError("Mastodon status has no ID")
        return str(status_id)

    def _public_error(self, exc: MastodonError) -> MastodonCollectorError:
        if (
            self.timeline == "hashtag"
            and not self.has_access_token
            and isinstance(exc, MastodonAPIError)
            and len(exc.args) > 1
            and exc.args[1] in {401, 422}
        ):
            return MastodonCollectorError(
                "This Mastodon instance requires an access token to collect hashtags",
                "mastodon_access_token_required",
            )
        if isinstance(exc, MastodonUnauthorizedError):
            return MastodonCollectorError("Mastodon authentication failed or access was denied", "mastodon_authentication_failed")
        if isinstance(exc, MastodonNotFoundError):
            return MastodonCollectorError("The configured Mastodon timeline or account was not found", "mastodon_not_found")
        if isinstance(exc, MastodonRatelimitError):
            return MastodonCollectorError("Mastodon rate limit exceeded; increase the refresh interval", "mastodon_rate_limited")
        if isinstance(exc, MastodonNetworkError):
            return MastodonCollectorError("The Mastodon instance could not be reached", "mastodon_unavailable")
        if isinstance(exc, MastodonAPIError):
            return MastodonCollectorError("The Mastodon instance rejected the collection request", "mastodon_api_error")
        return MastodonCollectorError("Mastodon collection failed", "mastodon_collection_failed")

    def _setup(self, source: dict[str, Any]) -> None:
        parameters = source["parameters"]
        self.instance_url = str(parameters["INSTANCE_URL"]).rstrip("/")
        self.timeline = str(parameters["TIMELINE"])
        self.collection_mode = str(parameters.get("COLLECTION_MODE", "complete"))
        access_token = str(parameters.get("ACCESS_TOKEN") or "").strip()
        self.has_access_token = bool(access_token)
        self.mastodon_cursor = source.get("mastodon_cursor") if isinstance(source.get("mastodon_cursor"), dict) else None
        self.skipped_statuses = False
        if self.has_access_token and not self.instance_url.startswith("https://"):
            raise MastodonCollectorError(
                "Mastodon access tokens require an HTTPS instance URL",
                "mastodon_https_required",
            )

        self.client = Mastodon(
            access_token=access_token or None,
            api_base_url=self.instance_url,
            ratelimit_method="throw",
            request_timeout=60,
            user_agent=parameters.get("USER_AGENT") or "TaranisAI/1.0",
        )
        if proxy_server := parameters.get("PROXY_SERVER"):
            self.client.session.proxies.update({"http": proxy_server, "https": proxy_server})

        if self.timeline == "hashtag":
            self.target = str(parameters["HASHTAG"]).lstrip("#").strip()
        elif self.timeline == "home":
            self.target = str(self.client.account_verify_credentials()["id"])
        else:
            account = str(parameters["ACCOUNT"]).lstrip("@").strip()
            self.target = str(self.client.account_lookup(account)["id"])

    def _timeline_key(self) -> str:
        target = self.target.casefold() if self.timeline == "hashtag" else self.target
        return f"{self.instance_url}|{self.timeline}|{target}"

    def _fetch_page(
        self,
        *,
        min_id: str | None = None,
        since_id: str | None = None,
        limit: int = MASTODON_PAGE_SIZE,
    ) -> list[Any]:
        if self.client is None:
            raise RuntimeError("Mastodon collector is not configured")
        pagination = {"limit": limit, "min_id": min_id, "since_id": since_id}
        if self.timeline == "hashtag":
            page = self.client.timeline_hashtag(self.target, **pagination)
        elif self.timeline == "home":
            page = self.client.timeline_home(**pagination)
        else:
            page = self.client.account_statuses(self.target, **pagination)
        return list(page)

    def _fetch_statuses(self, *, use_cursor: bool) -> list[Any]:
        timeline_key = self._timeline_key()
        stored_cursor = self.mastodon_cursor or {}
        last_status_id = stored_cursor.get("last_status_id") if stored_cursor.get("timeline") == timeline_key else None
        if last_status_id and use_cursor:
            if self.collection_mode == "latest":
                page = self._fetch_page(since_id=last_status_id)
                if not page or self._status_id(page[0]) == last_status_id:
                    return []
                oldest_status = self._fetch_page(min_id=last_status_id, limit=1)
                page_ids = {self._status_id(status) for status in page}
                self.skipped_statuses = bool(oldest_status and self._status_id(oldest_status[0]) not in page_ids)
                return page

            statuses: list[Any] = []
            forward_cursor = last_status_id
            while True:
                page = self._fetch_page(min_id=forward_cursor)
                if not page:
                    break
                next_cursor = self._status_id(page[0])
                if next_cursor == forward_cursor:
                    break
                statuses = page + statuses
                forward_cursor = next_cursor
            return statuses

        return self._fetch_page()

    def _news_item(self, status: Any, source_id: str) -> NewsItem:
        post = status.get("reblog") or status
        account = post.get("account") or {}
        link = str(post.get("url") or post.get("uri") or "")
        if not link:
            raise ValueError("Mastodon status has no URL")
        author = str(account.get("display_name") or account.get("acct") or "")
        content = self._plain_text(post.get("content"))
        if not content:
            descriptions = [
                self._plain_text(attachment.get("description"))
                for attachment in post.get("media_attachments") or []
                if attachment.get("description")
            ]
            content = " ".join(descriptions)
        title = self._plain_text(post.get("spoiler_text")) or content
        if len(title) > 160:
            title = f"{title[:157].rstrip()}..."
        if not title:
            title = f"Mastodon post by {author or 'unknown account'}"

        return NewsItem(
            osint_source_id=source_id,
            author=author,
            title=title,
            content=content,
            link=link,
            source=str(account.get("url") or self.instance_url),
            published=post.get("created_at"),
            language=post.get("language"),
        )

    def _gather(self, source: dict[str, Any], *, use_cursor: bool) -> tuple[list[Any], list[NewsItem]]:
        try:
            self._setup(source)
            statuses = self._fetch_statuses(use_cursor=use_cursor)
            return statuses, [self._news_item(status, str(source["id"])) for status in statuses]
        except MastodonError as exc:
            logger.error("Mastodon API request failed")
            raise self._public_error(exc) from exc
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Mastodon returned an invalid response")
            raise MastodonCollectorError("Mastodon returned an invalid response", "mastodon_invalid_response") from exc

    def collect(self, source: dict[str, Any], manual: bool = False):
        statuses, news_items = self._gather(source, use_cursor=True)
        previous_cursor = self.mastodon_cursor
        if not statuses:
            raise NoChangeError("No new Mastodon statuses")

        next_cursor = {"timeline": self._timeline_key(), "last_status_id": self._status_id(statuses[0])}
        try:
            result = self.publish(news_items, source)
        except NoChangeError as exc:
            self.mastodon_cursor = next_cursor
            if self.skipped_statuses:
                raise NoChangeError(f"{exc}; {MASTODON_SKIP_MESSAGE}") from exc
            raise
        except Exception as exc:
            self.mastodon_cursor = previous_cursor
            logger.exception("Publishing Mastodon statuses failed")
            raise MastodonCollectorError(
                "Collected Mastodon statuses could not be published",
                "mastodon_publish_failed",
            ) from exc
        self.mastodon_cursor = next_cursor
        if self.skipped_statuses:
            return f"{result}; {MASTODON_SKIP_MESSAGE}"
        return result

    def preview_collector(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        _, news_items = self._gather(source, use_cursor=False)
        return self.preview(news_items, source)
