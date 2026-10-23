from collections import defaultdict
from collections.abc import Iterable
from math import ceil
from typing import Any, Literal

from models.cti import CanonicalIOCType, CTIItem, CTIResponse, normalize_ioc_type, normalize_ioc_value
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from core.managers.db_manager import db
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFinding, AssetSbomImport
from core.model.ioc import IOC
from core.model.news_item import NewsItem
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User
from core.service.asset_findings import cve_tag_query, finding_response


ASSET_CTI_PAGE_SIZE = 50


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
    def get_asset_cti(cls, asset_id: str, user: User | None, page: int = 1, search: str = "") -> tuple[dict, int]:
        from core.model.asset import Asset

        if not user or Asset.get_for_api(asset_id, user.organization)[1] != 200:
            return {"error": "Asset not found"}, 404
        asset = Asset.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}, 404

        return cls._asset_response(asset_id, [asset], user, page, search), 200

    @classmethod
    def get_assets_cti(cls, user: User | None, page: int = 1, search: str = "") -> tuple[dict, int]:
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
        return cls._asset_response("all", assets, user, page, search), 200

    @classmethod
    def _asset_response(cls, item_id: str, assets: Iterable[Any], user: User, page: int, search: str) -> dict:
        from core.service.asset_intelligence import article_visible

        assets_by_id = {asset.id: asset for asset in assets}
        news_items_by_id: dict[str, NewsItem] = {}
        extra_iocs: set[tuple[CanonicalIOCType, str]] = set()
        can_assess = "ASSESS_ACCESS" in user.get_permissions()
        for asset in assets_by_id.values():
            for observable in asset.asset_observables:
                if ioc_type := normalize_ioc_type(observable.ioc_type):
                    extra_iocs.add((ioc_type, normalize_ioc_value(observable.value, ioc_type)))
            if not can_assess:
                continue
            for vulnerability in asset.vulnerabilities:
                report = vulnerability.report_item
                if report and report.access_allowed(user, False):
                    for story in report.stories:
                        if Story.get_for_api(story.id, user)[1] == 200:
                            news_items_by_id.update((n.id, n) for n in story.news_items if article_visible(n, user))
        existing = cls._response("asset", item_id, news_items_by_id.values(), extra_iocs=extra_iocs, include_enrichment=False)
        items = {(item["ioc_type"], item["value"]): item for item in existing["iocs"] if search.casefold() in item["value"].casefold()}
        for item in items.values():
            item["findings"] = []
        records = {r.id: r for r in db.session.scalars(db.select(AssetSbomImport).where(AssetSbomImport.asset_id.in_(assets_by_id)))}
        catalog = select(AssetSbomFinding.id, AssetSbomFinding.identifier, AssetSbomFinding.cve_id).where(
            AssetSbomFinding.import_id.in_(records)
        )
        if search:
            pattern = f"%{search}%"
            catalog = catalog.where(
                or_(
                    AssetSbomFinding.identifier.ilike(pattern),
                    AssetSbomFinding.components.any(
                        or_(
                            AssetSbomComponent.inventory["name"].as_string().ilike(pattern),
                            AssetSbomComponent.inventory["purl"].as_string().ilike(pattern),
                        )
                    ),
                )
            )
        finding_ids: dict[tuple[str, str], list[str]] = defaultdict(list)
        for finding_id, identifier, cve_id in db.session.execute(catalog):
            key = ("cve" if cve_id else "vulnerability", cve_id or identifier)
            finding_ids[key].append(finding_id)
            items.setdefault(key, {"ioc_type": key[0], "value": key[1], "news_item_ids": [], "enrichment": None, "findings": []})
        keys = sorted(items)
        pages = max(1, ceil(len(keys) / ASSET_CTI_PAGE_SIZE))
        page = min(pages, max(1, page))
        selected = keys[(page - 1) * ASSET_CTI_PAGE_SIZE : page * ASSET_CTI_PAGE_SIZE]
        selected_ids = [finding_id for key in selected for finding_id in finding_ids[key]]
        findings = db.session.scalars(
            db.select(AssetSbomFinding).where(AssetSbomFinding.id.in_(selected_ids)).options(selectinload(AssetSbomFinding.components))
        )
        for finding in findings:
            record = records[finding.import_id]
            key = ("cve" if finding.cve_id else "vulnerability", finding.cve_id or finding.identifier)
            items[key]["findings"].append(finding_response(finding, record, assets_by_id[record.asset_id].name))
        if can_assess:
            visible = Story.visible_query(user).with_only_columns(Story.id)
            associations = cve_tag_query(list(assets_by_id)).where(
                AssetSbomFinding.cve_id.in_([value for kind, value in selected if kind == "cve"]), NewsItem.story_id.in_(visible)
            )
            for article, finding in db.session.execute(associations):
                if article_visible(article, user):
                    item = items[("cve", finding.cve_id)]
                    item["news_item_ids"] = sorted(set(item["news_item_ids"]) | {article.id})
        enrichments = IOC.get_for_iocs(set(selected))
        for key in selected:
            if enrichment := enrichments.get(key[1]):
                items[key]["enrichment"] = enrichment.to_cti_model()
        return CTIResponse(
            item_type="asset",
            item_id=item_id,
            iocs=[items[key] for key in selected],
            pagination={"page": page, "pages": pages, "total": len(keys), "search": search},
        ).model_dump(mode="json")

    @classmethod
    def _response(
        cls,
        item_type: Literal["news_item", "story", "report", "asset"],
        item_id: str,
        news_items: Iterable[NewsItem],
        extra_iocs: Iterable[tuple[CanonicalIOCType, str]] = (),
        *,
        include_enrichment: bool = True,
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

        enrichments = IOC.get_for_iocs(set(news_item_ids_by_ioc)) if include_enrichment else {}
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
        return response.model_dump(mode="json", exclude_none=False, exclude={"pagination": True, "iocs": {"__all__": {"findings"}}})
