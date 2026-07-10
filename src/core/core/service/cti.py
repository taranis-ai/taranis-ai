from collections import defaultdict
from typing import Any, Iterable, Literal

from models.cti import CanonicalIOCType, CTIItem, CTIResponse, normalize_ioc_type, normalize_ioc_value
from sqlalchemy.orm import selectinload

from core.model.ioc import IOC
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
    def get_asset_cti(cls, asset_id: str, user: User | None) -> tuple[dict, int]:
        from core.model.asset import Asset

        if not user or Asset.get_for_api(asset_id, user.organization)[1] != 200:
            return {"error": "Asset not found"}, 404
        asset = Asset.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}, 404

        return cls._asset_response(asset_id, [asset], user), 200

    @classmethod
    def get_assets_cti(cls, user: User | None) -> tuple[dict, int]:
        from core.model.asset import Asset, AssetVulnerability

        if not user:
            return {"error": "Asset not found"}, 404
        asset_reports = selectinload(Asset.vulnerabilities).selectinload(AssetVulnerability.report_item)
        query = Asset.get_filter_query({"organization": user.organization}).options(
            selectinload(Asset.asset_observables),
            asset_reports.selectinload(ReportItem.attributes),
            asset_reports.selectinload(ReportItem.stories).selectinload(Story.news_items).selectinload(NewsItem.tags),
        )
        assets = Asset.get_filtered(query) or []
        return cls._asset_response("all", assets, user), 200

    @classmethod
    def _asset_response(cls, item_id: str, assets: Iterable[Any], user: User) -> dict:
        news_items_by_id: dict[str, NewsItem] = {}
        extra_iocs: set[tuple[CanonicalIOCType, str]] = set()
        for asset in assets:
            for observable in asset.asset_observables:
                if ioc_type := normalize_ioc_type(observable.ioc_type):
                    extra_iocs.add((ioc_type, normalize_ioc_value(observable.value, ioc_type)))
            for vulnerability in asset.vulnerabilities:
                report = vulnerability.report_item
                if not report or not report.access_allowed(user, False):
                    continue
                news_items_by_id.update({news_item.id: news_item for story in report.stories for news_item in story.news_items})
        return cls._response("asset", item_id, news_items_by_id.values(), extra_iocs=extra_iocs)

    @classmethod
    def _response(
        cls,
        item_type: Literal["news_item", "story", "report", "asset"],
        item_id: str,
        news_items: Iterable[NewsItem],
        extra_iocs: Iterable[tuple[CanonicalIOCType, str]] = (),
    ) -> dict:
        news_item_ids_by_ioc: dict[tuple[CanonicalIOCType, str], set[str]] = defaultdict(set)
        for news_item in news_items:
            for tag in news_item.tags:
                if not (ioc_type := normalize_ioc_type(tag.tag_type)):
                    continue
                value = normalize_ioc_value(tag.name, ioc_type)
                if value:
                    news_item_ids_by_ioc[(ioc_type, value)].add(news_item.id)
        for ioc_type, value in extra_iocs:
            if value:
                news_item_ids_by_ioc.setdefault((ioc_type, value), set())

        enrichments = IOC.get_for_iocs(set(news_item_ids_by_ioc))
        response = CTIResponse(
            item_type=item_type,
            item_id=item_id,
            iocs=[
                CTIItem(
                    ioc_type=ioc_type,
                    value=value,
                    news_item_ids=sorted(news_item_ids),
                    enrichment=enrichments[value].to_cti_model() if value in enrichments else None,
                )
                for (ioc_type, value), news_item_ids in sorted(news_item_ids_by_ioc.items())
            ],
        )
        return response.model_dump(mode="json", exclude_none=False)
