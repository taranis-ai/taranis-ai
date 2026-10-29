"""Qualify current asset associations for Assess counts, pages and evidence."""

from dataclasses import dataclass

from models.assess import ASSESS_FILTER_KEYS, AssessSearchFilters
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch
from core.model.asset_sbom import AssetSbomFinding, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User
from core.service.asset_findings import finding_cvss_ratings
from core.service.asset_intelligence import STORY_BATCH_SIZE, article_intelligence, matching_stories


@dataclass
class ArticleAssetMatch:
    item: NewsItem
    asset: Asset
    software_matches: list[tuple[AssetArticleMatch, list[dict]]]
    findings: list[AssetSbomFinding]
    ratings: dict[str, list[dict]]
    max_cvss: float | None

    def evidence(self) -> dict:
        article = article_intelligence(self.software_matches, self.findings, self.item)
        for cve in article["cve_matches"]:
            cve["ratings"] = self.ratings[cve["finding_id"]]
        return {
            **article,
            "asset_id": self.asset.id,
            "asset_name": self.asset.name,
            "group_name": self.asset.asset_group.name,
            "software_match": bool(self.software_matches),
            "max_cvss": self.max_cvss,
        }


def matches_choice(choice: str, present: bool) -> bool:
    return choice == "any" or present == (choice == "yes")


def qualify_article_asset(item, asset, matches, findings, filters: AssessSearchFilters) -> ArticleAssetMatch | None:
    if filters.asset_cve_ids:
        findings = [finding for finding in findings if finding.cve_id in filters.asset_cve_ids]
        if not findings:
            return None
    if not matches and not findings:
        return None
    if not matches_choice(filters.asset_cve_match, bool(findings)) or not matches_choice(filters.asset_software_match, bool(matches)):
        return None
    ratings = {finding.id: finding_cvss_ratings(finding) for finding in findings}
    highest_cvss = max((r["score"] for scores in ratings.values() for r in scores), default=None)
    if filters.asset_cvss_min is not None and (highest_cvss is None or highest_cvss < filters.asset_cvss_min):
        return None
    if filters.asset_cvss_max is not None and (highest_cvss is None or highest_cvss > filters.asset_cvss_max):
        return None
    return ArticleAssetMatch(item, asset, matches, findings, ratings, highest_cvss)


def qualifying_story_associations(matches, tagged, imports: dict[str, Asset], filters: AssessSearchFilters) -> list[ArticleAssetMatch]:
    pairs = {}
    for match, evidence in matches:
        if asset := imports.get(match.trigger.component.import_id):
            pair = pairs.setdefault((match.news_item_id, asset.id), {"item": match.news_item, "asset": asset, "matches": [], "findings": []})
            pair["matches"].append((match, evidence))
    for item, finding in tagged:
        if asset := imports.get(finding.import_id):
            pair = pairs.setdefault((item.id, asset.id), {"item": item, "asset": asset, "matches": [], "findings": []})
            pair["findings"].append(finding)
    associations = [association for pair in pairs.values() if (association := qualify_article_asset(**pair, filters=filters))]
    if filters.asset_cve_ids:
        # Clustered stories may cover a host's CVEs in separate articles; never borrow another host's CVE.
        asset_cves: dict[str, set[str]] = {}
        for association in associations:
            asset_cves.setdefault(association.asset.id, set()).update(f.cve_id for f in association.findings)
        associations = [a for a in associations if filters.asset_cve_ids.issubset(asset_cves[a.asset.id])]
    return associations


def accessible_assets(user: User) -> list[Asset]:
    return list(
        db.session.scalars(
            select(Asset)
            .join(AssetGroup)
            .where(or_(AssetGroup.organization_id == user.organization.id, AssetGroup.id == AssetGroup.get_default_group().id))
            .options(joinedload(Asset.asset_group), selectinload(Asset.asset_tags))
            .order_by(Asset.name, Asset.id)
        )
    )


def asset_filter_lists(user: User) -> dict:
    assets = accessible_assets(user)
    groups = {a.asset_group_id: {"id": a.asset_group_id, "name": a.asset_group.name} for a in assets}
    return {
        "assets": [{"id": a.id, "name": a.name, "group_id": a.asset_group_id} for a in assets],
        "groups": sorted(groups.values(), key=lambda group: (group["name"].casefold(), group["id"])),
        "tags": sorted({tag.name for asset in assets for tag in asset.asset_tags}),
    }


def matching_asset_stories(user: User, filters: AssessSearchFilters, story_query: Select):
    assets = {
        a.id: a
        for a in accessible_assets(user)
        if (not filters.asset_id or a.id == filters.asset_id)
        and (not filters.asset_group_id or a.asset_group_id == filters.asset_group_id)
        and (not filters.asset_tag or any(tag.name == filters.asset_tag for tag in a.asset_tags))
    }
    if not assets:
        return
    imports = {
        import_id: assets[asset_id]
        for import_id, asset_id in db.session.execute(
            select(AssetSbomImport.id, AssetSbomImport.asset_id).where(AssetSbomImport.asset_id.in_(assets))
        )
        if asset_id is not None
    }
    for matches, tagged in matching_stories(list(assets), user, filters, story_query):
        if associations := qualifying_story_associations(matches, tagged, imports, filters):
            yield associations[0].item.story_id, associations


def summarize_asset_matches(associations: list[ArticleAssetMatch]) -> list[dict]:
    """Summarize each asset across the story's qualifying article associations."""
    asset_associations: dict[str, list[ArticleAssetMatch]] = {}
    for association in associations:
        asset_associations.setdefault(association.asset.id, []).append(association)
    return [
        {
            "id": matches[0].asset.id,
            "name": matches[0].asset.name,
            "max_cvss": max((match.max_cvss for match in matches if match.max_cvss is not None), default=None),
            "cve_count": len({finding.cve_id for match in matches for finding in match.findings}),
            "software_match": any(match.software_matches for match in matches),
        }
        for matches in sorted(asset_associations.values(), key=lambda matches: (matches[0].asset.name.casefold(), matches[0].asset.id))
    ]


def assess_match_page(user: User, story_query: Select, filter_args: dict) -> tuple[dict[str, list[dict]], dict[str, int] | None]:
    """Count matches in bounded batches, retaining only the requested page's asset summaries."""
    filters = AssessSearchFilters.model_validate({key: value for key, value in filter_args.items() if key in ASSESS_FILTER_KEYS})
    page_assets: dict[str, list[dict]] = {}
    counts = dict.fromkeys(("total_count", "read_count", "important_count", "in_reports_count"), 0)
    include_counts = not filter_args.get("no_count", False)
    offset, limit = int(filter_args.get("offset", 0)), int(filter_args.get("limit") or 0)
    count_batch = []

    def accumulate_counts() -> None:
        totals = Story.get_additional_counts(story_query.where(Story.id.in_(count_batch)))._mapping
        for key in counts:
            counts[key] += totals[key]
        count_batch.clear()

    for position, (story_id, associations) in enumerate(matching_asset_stories(user, filters, story_query)):
        if position >= offset and (not limit or len(page_assets) < limit):
            page_assets[story_id] = summarize_asset_matches(associations)
        if include_counts:
            count_batch.append(story_id)
            if len(count_batch) == STORY_BATCH_SIZE:
                accumulate_counts()
        elif limit and len(page_assets) == limit:
            break
    if count_batch:
        accumulate_counts()
    return page_assets, counts if include_counts else None


def story_asset_evidence(user: User, story_id: str, filters: AssessSearchFilters) -> dict:
    query = Story.get_filter_query({**filters.to_query_params(), "_user": user}).where(Story.id == story_id)
    articles: dict[str, dict] = {}
    for _, associations in matching_asset_stories(user, filters, query):
        for association in associations:
            article = articles.setdefault(association.item.id, {"id": association.item.id, "title": association.item.title, "hosts": []})
            article["hosts"].append(association.evidence())
    for article in articles.values():
        article["hosts"].sort(key=lambda host: (host["asset_name"].casefold(), host["asset_id"]))
        article["cve_count"] = len({cve["cve_id"] for host in article["hosts"] for cve in host["cve_matches"]})
    return {"story_id": story_id, "articles": [articles[key] for key in sorted(articles)]}
