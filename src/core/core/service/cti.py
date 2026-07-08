from collections import defaultdict
from typing import Iterable, Literal

from models.cti import CanonicalIOCType, CTIItem, CTIResponse, normalize_ioc_type, normalize_ioc_value

from core.model.intelowl_enrichment import IntelOwlEnrichment
from core.model.news_item import NewsItem
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User


class CTIService:
    @classmethod
    def get_news_item_cti(cls, news_item_id: str, user: User | None) -> tuple[dict, int]:
        item = NewsItem.get(news_item_id)
        if not item:
            return {"error": "NewsItem not found"}, 404
        if user and not item.allowed_with_acl(user, require_write_access=False):
            return {"error": "User does not have access to this news item"}, 403
        return cls._response("news_item", news_item_id, [item]), 200

    @classmethod
    def get_story_cti(cls, story_id: str, user: User | None) -> tuple[dict, int]:
        _, status = Story.get_for_api(story_id, user)
        if status != 200:
            return {"error": "Story not found" if status == 404 else "User is not allowed to read story"}, status
        item = Story.get(story_id)
        if not item:
            return {"error": "Story not found"}, 404
        return cls._response("story", story_id, item.news_items), 200

    @classmethod
    def get_report_cti(cls, report_id: str, user: User | None) -> tuple[dict, int]:
        _, status = ReportItem.get_for_api(report_id, user)
        if status != 200:
            return {"error": "Report Item not found" if status == 404 else "User is not allowed to read report"}, status
        report = ReportItem.get(report_id)
        if not report:
            return {"error": "Report Item not found"}, 404
        news_items = [news_item for story in report.stories for news_item in story.news_items]
        return cls._response("report", report_id, news_items), 200

    @classmethod
    def _response(cls, item_type: Literal["news_item", "story", "report"], item_id: str, news_items: Iterable[NewsItem]) -> dict:
        news_item_ids_by_ioc: dict[tuple[CanonicalIOCType, str], set[str]] = defaultdict(set)
        for news_item in news_items:
            for tag in news_item.tags:
                if not (ioc_type := normalize_ioc_type(tag.tag_type)):
                    continue
                value = normalize_ioc_value(tag.name, ioc_type)
                if value:
                    news_item_ids_by_ioc[(ioc_type, value)].add(news_item.id)

        enrichments = IntelOwlEnrichment.get_for_iocs(set(news_item_ids_by_ioc))
        response = CTIResponse(
            item_type=item_type,
            item_id=item_id,
            iocs=[
                CTIItem(
                    ioc_type=ioc_type,
                    value=value,
                    news_item_ids=sorted(news_item_ids),
                    enrichment=enrichments[(ioc_type, value)].to_cti_model() if (ioc_type, value) in enrichments else None,
                )
                for (ioc_type, value), news_item_ids in sorted(news_item_ids_by_ioc.items())
            ],
        )
        return response.model_dump(mode="json", exclude_none=False)
