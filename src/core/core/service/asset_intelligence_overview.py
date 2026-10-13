"""Filter current article/host associations before grouping and pagination."""

from models.asset_intelligence import IntelligenceFilters
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload, selectinload

from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch
from core.model.asset_sbom import AssetSbomFinding, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.user import User
from core.service.asset_findings import finding_cvss_ratings
from core.service.asset_intelligence import STORIES_PER_PAGE, article_intelligence, matching_stories


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
    findings = [finding for finding in findings if any(c.id in selected for c in finding.components)]
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
    for pair in pairs.values():
        if (host := host_intelligence(pair["matches"], pair["findings"], pair["item"], filters)) is None:
            continue
        asset = pair["asset"]
        host.update(asset_id=asset.id, asset_name=asset.name, group_id=asset.asset_group_id, group_name=asset.asset_group.name)
        article = articles.setdefault(host["id"], {"id": host["id"], "title": host["title"], "hosts": []})
        article["hosts"].append(host)
    if not articles:
        return None
    for article in articles.values():
        article["hosts"].sort(key=lambda host: (host["asset_name"].casefold(), host["asset_id"]))
        article["cve_count"] = len({cve["cve_id"] for host in article["hosts"] for cve in host["cve_matches"]})
    story = matches[0][0].news_item.story if matches else tagged[0][0].story
    return {"id": story.id, "title": story.title, "articles": [articles[key] for key in sorted(articles)]}


def intelligence_overview(user: User, filters: IntelligenceFilters) -> dict:
    # Match individual asset access: the shared default group plus the user's organization.
    catalog = list(
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
    needs_cve = filters.cve_match == "yes" or filters.cvss_available == "yes" or filters.cvss_min is not None or filters.cvss_max is not None
    if assets:
        for matches, tagged in matching_stories(list(assets), user, cve_only=needs_cve):
            if story := overview_story(matches, tagged, imports, filters):
                results.append(story)
            if len(results) > filters.page * STORIES_PER_PAGE:
                break
    groups = {a.asset_group_id: {"id": a.asset_group_id, "name": a.asset_group.name} for a in catalog}
    return {
        "items": results[(filters.page - 1) * STORIES_PER_PAGE : filters.page * STORIES_PER_PAGE],
        "page": filters.page,
        "has_more": len(results) > filters.page * STORIES_PER_PAGE,
        "filters": filters.model_dump(exclude={"page"}),
        "assets": [{"id": a.id, "name": a.name, "group_id": a.asset_group_id} for a in catalog],
        "tags": sorted({tag.name for asset in catalog for tag in asset.asset_tags}),
        "groups": sorted(groups.values(), key=lambda group: (group["name"].casefold(), group["id"])),
    }
