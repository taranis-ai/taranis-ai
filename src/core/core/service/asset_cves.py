"""Read CVEs from current inventories and manual asset observables only."""

import re
from collections import defaultdict
from itertools import groupby

from models.asset_cve import CVE_SEVERITIES, AssetCve, AssetCveFilters, AssetCveSummary, CveSeverity
from models.cti import normalize_ioc_value
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup, AssetObservable, AssetTag
from core.model.asset_sbom import AssetSbomFinding, AssetSbomImport
from core.model.user import User
from core.service.asset_findings import valid_cvss_rating


def accessible_assets_query(user: User):
    return (
        select(Asset)
        .join(AssetGroup)
        .where(or_(AssetGroup.organization_id == user.organization.id, AssetGroup.id == AssetGroup.get_default_group().id))
    )


def cve_severity(score: float | None, reported: set[str]) -> CveSeverity:
    if score is not None:
        for threshold, severity in ((9, "critical"), (7, "high"), (4, "medium")):
            if score >= threshold:
                return severity
        return "low" if score > 0 else "none"
    return next((severity for severity in CVE_SEVERITIES if severity in reported), "unknown")


def asset_cves(asset_ids: list[str]):
    """Yield each asset/CVE once, streaming source records and merging manual entries."""
    manual = defaultdict(set)
    for asset_id, value in db.session.execute(
        select(AssetObservable.asset_id, AssetObservable.value).where(
            AssetObservable.asset_id.in_(asset_ids), AssetObservable.ioc_type == "cve"
        )
    ):
        cve_id = normalize_ioc_value(value, "cve")
        if re.fullmatch(r"CVE-\d{4}-\d{4,}", cve_id):
            manual[asset_id].add(cve_id)
    query = (
        select(AssetSbomImport.asset_id, AssetSbomFinding.cve_id, AssetSbomFinding.details)
        .join(AssetSbomFinding, AssetSbomFinding.import_id == AssetSbomImport.id)
        .where(AssetSbomImport.asset_id.in_(asset_ids), AssetSbomFinding.cve_id != "")
        .order_by(AssetSbomImport.asset_id, AssetSbomFinding.cve_id)
        .execution_options(yield_per=200)
    )
    for (asset_id, cve_id), findings in groupby(db.session.execute(query), key=lambda row: (row[0], row[1])):
        assert asset_id is not None  # The asset-ID filter excludes unconfirmed previews.
        score, reported, sources = None, set(), set()
        for _, _, details in findings:
            for record in details["records"]:
                if name := (record.get("source") or {}).get("name"):
                    sources.add(name)
                for rating in record.get("ratings", []):
                    if name := (rating.get("source") or {}).get("name"):
                        sources.add(name)
                    reported.add(str(rating.get("severity", "")).lower())
                    if validated := valid_cvss_rating(rating):
                        score = max(score if score is not None else 0, validated["score"])
        if "info" in reported:
            reported.add("none")
        entry = AssetCve(
            cve_id=cve_id,
            score=score,
            severity=cve_severity(score, reported),
            imported=True,
            manual=cve_id in manual[asset_id],
            sources=sorted(sources),
        )
        manual[asset_id].discard(cve_id)
        yield asset_id, entry
    for asset_id, values in manual.items():
        for cve_id in sorted(values):
            yield asset_id, AssetCve(cve_id=cve_id, manual=True)


def cve_overview(user: User, filters: AssetCveFilters) -> dict:
    accessible = accessible_assets_query(user)
    query = accessible
    if filters.search:
        query = query.where(Asset.name.icontains(filters.search, autoescape=True))
    if filters.group:
        query = query.where(Asset.asset_group_id == filters.group)
    if filters.tag:
        query = query.where(Asset.asset_tags.any(AssetTag.name == filters.tag.lower()))
    total = db.session.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = min(filters.page, max(1, (total + filters.limit - 1) // filters.limit))
    assets = db.session.scalars(
        query.options(joinedload(Asset.asset_group), selectinload(Asset.asset_tags))
        .order_by(func.lower(Asset.name), Asset.id)
        .offset((page - 1) * filters.limit)
        .limit(filters.limit)
    )
    summaries = {
        asset.id: AssetCveSummary(
            id=asset.id, name=asset.name, group_name=asset.asset_group.name, tags=sorted(tag.name for tag in asset.asset_tags)
        )
        for asset in assets
    }
    for asset_id, cve in asset_cves(list(summaries)):
        summaries[asset_id].counts[cve.severity] += 1
        summaries[asset_id].total += 1
    groups = db.session.execute(
        select(AssetGroup.id, AssetGroup.name)
        .where(AssetGroup.id.in_(accessible.with_only_columns(Asset.asset_group_id)))
        .order_by(AssetGroup.name, AssetGroup.id)
    ).mappings()
    tags = db.session.scalars(
        select(AssetTag.name).where(AssetTag.asset_id.in_(accessible.with_only_columns(Asset.id))).distinct().order_by(AssetTag.name)
    )
    return {
        "items": [summary.model_dump() for summary in summaries.values()],
        "total_count": total,
        "page": page,
        "limit": filters.limit,
        "groups": [dict(group) for group in groups],
        "tags": list(tags),
    }


def cve_list(user: User, asset_id: str, filters: AssetCveFilters) -> tuple[dict, int]:
    asset = db.session.scalar(accessible_assets_query(user).where(Asset.id == asset_id))
    if not asset:
        return {"error": "Asset not found."}, 404
    entries = sorted(
        (
            entry
            for _, entry in asset_cves([asset.id])
            if (not filters.severity or entry.severity == filters.severity) and filters.search.casefold() in entry.cve_id.casefold()
        ),
        key=lambda entry: (CVE_SEVERITIES.index(entry.severity), -(entry.score or 0), entry.cve_id),
    )
    total = len(entries)
    page = min(filters.page, max(1, (total + filters.limit - 1) // filters.limit))
    return {
        "asset_id": asset.id,
        "asset_name": asset.name,
        "items": [entry.model_dump() for entry in entries[(page - 1) * filters.limit : page * filters.limit]],
        "total_count": total,
        "page": page,
        "limit": filters.limit,
    }, 200
