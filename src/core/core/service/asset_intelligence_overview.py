"""Filter current article/host associations before grouping and pagination."""

from models.asset_intelligence import IntelligenceFilters
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
from core.service.asset_intelligence import STORY_BATCH_SIZE, article_intelligence, matching_stories, product_identity


def matches_choice(choice: str, present: bool) -> bool:
    return choice == "any" or present == (choice == "yes")


def host_intelligence(
    matches: list[tuple[AssetArticleMatch, list[dict]]], findings: list[AssetSbomFinding], item: NewsItem, filters: IntelligenceFilters
) -> dict | None:
    components = {match.trigger.component.id: match.trigger.component for match, _ in matches}
    components.update((c.id, c) for finding in findings for c in finding.components)
    search = filters.package.casefold()
    selected = {c.id for c in components.values() if any(search in c.inventory.get(field, "").casefold() for field in ("name", "purl"))}
    matches = [(m, evidence) for m, evidence in matches if m.trigger.component_id in selected]
    findings = [
        finding
        for finding in findings
        if (not filters.cve_id or finding.cve_id == filters.cve_id) and any(c.id in selected for c in finding.components)
    ]
    if filters.cve_id and not findings:
        return None
    if not matches and not findings:
        return None
    if not matches_choice(filters.cve_match, bool(findings)) or not matches_choice(filters.package_match, bool(matches)):
        return None

    article = article_intelligence(matches, findings, item, allowed_component_ids=selected)
    ratings_by_finding: dict[str, list[dict]] = {
        finding.id: [
            {**rating, "component_ids": sorted(selected.intersection(rating["component_ids"]))}
            for rating in finding_cvss_ratings(finding)
            if selected.intersection(rating["component_ids"])
        ]
        for finding in findings
    }
    for cve in article["cve_matches"]:
        cve["ratings"] = ratings_by_finding[cve["finding_id"]]
    highest = max((r["score"] for ratings in ratings_by_finding.values() for r in ratings), default=None)
    if not matches_choice(filters.cvss_available, highest is not None):
        return None
    if filters.cvss_min is not None and (highest is None or highest < filters.cvss_min):
        return None
    if filters.cvss_max is not None and (highest is None or highest > filters.cvss_max):
        return None
    return {**article, "package_match": bool(matches), "max_cvss": highest}


def overview_story(matches, tagged, imports: dict[str, Asset], filters: IntelligenceFilters) -> dict | None:
    pairs = {}
    for match, evidence in matches:
        if not (asset := imports.get(match.trigger.component.import_id)):
            continue
        pair = pairs.setdefault((match.news_item_id, asset.id), {"item": match.news_item, "asset": asset, "matches": [], "findings": []})
        pair["matches"].append((match, evidence))
    for item, finding in tagged:
        if not (asset := imports.get(finding.import_id)):
            continue
        pair = pairs.setdefault((item.id, asset.id), {"item": item, "asset": asset, "matches": [], "findings": []})
        pair["findings"].append(finding)

    articles = {}
    packages = set()
    for pair in pairs.values():
        if (host := host_intelligence(pair["matches"], pair["findings"], pair["item"], filters)) is None:
            continue
        asset = pair["asset"]
        component_ids = {c["id"] for software in host["software"] for c in software["components"]}
        components = [match.trigger.component for match, _ in pair["matches"]]
        components.extend(c for finding in pair["findings"] for c in finding.components)
        packages.update((asset.id, product_identity(c.inventory)) for c in components if c.id in component_ids)
        host.update(asset_id=asset.id, asset_name=asset.name, group_id=asset.asset_group_id, group_name=asset.asset_group.name)
        article = articles.setdefault(host["id"], {"id": host["id"], "title": host["title"], "hosts": []})
        article["hosts"].append(host)
    if not articles:
        return None
    for article in articles.values():
        article["hosts"].sort(key=lambda host: (host["asset_name"].casefold(), host["asset_id"]))
        article["cve_count"] = len({cve["cve_id"] for host in article["hosts"] for cve in host["cve_matches"]})
    story = matches[0][0].news_item.story if matches else tagged[0][0].story
    return {"id": story.id, "title": story.title, "software_count": len(packages), "articles": [articles[key] for key in sorted(articles)]}


def accessible_assets(user: User) -> list[Asset]:
    # Match individual asset access: the shared default group plus the user's organization.
    return list(
        db.session.scalars(
            select(Asset)
            .join(AssetGroup)
            .where(
                or_(
                    AssetGroup.organization_id == user.organization.id,
                    AssetGroup.id == AssetGroup.get_default_group().id,
                )
            )
            .options(joinedload(Asset.asset_group), selectinload(Asset.asset_tags))
            .order_by(Asset.name, Asset.id)
        )
    )


def assess_match_page(user: User, story_query: Select, filter_args: dict) -> tuple[dict[str, list[dict]], dict[str, int] | None]:
    """Count current matches while retaining only the requested Assess page."""
    assets = {asset.id: asset for asset in accessible_assets(user)}
    import_asset_ids = dict(
        db.session.execute(select(AssetSbomImport.id, AssetSbomImport.asset_id).where(AssetSbomImport.asset_id.in_(assets))).all()
    )
    page_assets: dict[str, list[dict]] = {}
    counts = dict.fromkeys(("total_count", "read_count", "important_count", "in_reports_count"), 0)
    include_counts = not filter_args.get("no_count", False)
    offset, limit = int(filter_args.get("offset", 0)), int(filter_args.get("limit") or 0)
    matching_count = 0
    count_batch = []

    def accumulate_counts() -> None:
        totals = Story.get_additional_counts(story_query.where(Story.id.in_(count_batch)))._mapping
        for key in counts:
            counts[key] += totals[key]
        count_batch.clear()

    if assets:
        for matches, tagged in matching_stories(list(assets), user, IntelligenceFilters(), story_query):
            # Default overview filters accept either current phrase evidence or a CVE/component association.
            matched_imports = {match.trigger.component.import_id for match, _ in matches}
            matched_imports.update(finding.import_id for _, finding in tagged)
            matched_asset_ids = {asset_id for import_id in matched_imports if (asset_id := import_asset_ids.get(import_id)) in assets}
            if not matched_asset_ids:
                continue
            story_id = matches[0][0].news_item.story_id if matches else tagged[0][0].story_id
            if matching_count >= offset and (not limit or len(page_assets) < limit):
                page_assets[story_id] = [
                    {"id": asset.id, "name": asset.name}
                    for asset in sorted(
                        (assets[asset_id] for asset_id in matched_asset_ids), key=lambda asset: (asset.name.casefold(), asset.id)
                    )
                ]
            matching_count += 1
            if include_counts:
                count_batch.append(story_id)
                if len(count_batch) == STORY_BATCH_SIZE:
                    accumulate_counts()
            elif limit and len(page_assets) == limit:
                break
    if count_batch:
        accumulate_counts()
    return page_assets, counts if include_counts else None


def intelligence_overview(user: User, filters: IntelligenceFilters) -> dict:
    catalog = accessible_assets(user)
    assets = {
        a.id: a
        for a in catalog
        if (not filters.asset_id or a.id == filters.asset_id)
        and (not filters.group_id or a.asset_group_id == filters.group_id)
        and (not filters.tag or any(tag.name == filters.tag for tag in a.asset_tags))
    }
    imports = {
        import_id: assets[asset_id]
        for import_id, asset_id in db.session.execute(
            select(AssetSbomImport.id, AssetSbomImport.asset_id).where(AssetSbomImport.asset_id.in_(assets))
        )
        if asset_id is not None
    }
    results = []
    total_stories, total_articles = 0, 0
    start = (filters.page - 1) * filters.limit
    if assets:
        for matches, tagged in matching_stories(list(assets), user, filters):
            if not (story := overview_story(matches, tagged, imports, filters)):
                continue
            if start <= total_stories < start + filters.limit:
                results.append(story)
            total_stories += 1
            total_articles += len(story["articles"])
    groups = {a.asset_group_id: {"id": a.asset_group_id, "name": a.asset_group.name} for a in catalog}
    return {
        "items": results,
        "page": filters.page,
        "has_more": total_stories > filters.page * filters.limit,
        "total_stories": total_stories,
        "total_articles": total_articles,
        "page_size": filters.limit,
        "filters": filters.model_dump(mode="json", exclude={"page"}),
        "assets": [{"id": a.id, "name": a.name, "group_id": a.asset_group_id} for a in catalog],
        "tags": sorted({tag.name for asset in catalog for tag in asset.asset_tags}),
        "groups": sorted(groups.values(), key=lambda group: (group["name"].casefold(), group["id"])),
    }
