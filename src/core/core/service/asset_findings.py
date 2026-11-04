"""Read current imported findings and their associations with existing CVE tags."""

from math import isfinite

from models.cti import IOC_VALUE_PUNCTUATION
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.model.asset_sbom import AssetSbomFinding, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.news_item_tag import NewsItemTag


def cve_tag_query(asset_ids: list[str]):
    pairs = (
        select(NewsItemTag.news_item_id, AssetSbomFinding.id.label("finding_id"))
        .join(AssetSbomFinding, AssetSbomFinding.cve_id == func.upper(func.trim(func.trim(NewsItemTag.name), IOC_VALUE_PUNCTUATION)))
        .join(AssetSbomImport, AssetSbomImport.id == AssetSbomFinding.import_id)
        .where(
            AssetSbomImport.asset_id.in_(asset_ids),
            AssetSbomFinding.cve_id != "",
            AssetSbomFinding.matching_enabled.is_(True),
            func.lower(func.trim(NewsItemTag.tag_type)).in_(("cve", "cves")),
            AssetSbomFinding.components.any(),
        )
    )
    associations = pairs.distinct().subquery()
    return (
        select(NewsItem, AssetSbomFinding)
        .join(associations, associations.c.news_item_id == NewsItem.id)
        .join(AssetSbomFinding, AssetSbomFinding.id == associations.c.finding_id)
        .options(selectinload(AssetSbomFinding.components), selectinload(NewsItem.story))
    )


def finding_response(finding: AssetSbomFinding, record: AssetSbomImport, asset_name: str) -> dict:
    return {
        "id": finding.id,
        "asset_id": record.asset_id,
        "asset_name": asset_name,
        "identifier": finding.identifier,
        "matching_enabled": finding.matching_enabled,
        "imported_at": record.serialize_datetime(record.confirmed or record.created),
        "records": finding.details["records"],
        "unresolved_references": finding.details.get("unresolved_references", []),
        "component_references": {o["reference"]: c.id for c in finding.components for o in c.inventory["occurrences"]},
        "components": [
            {"id": c.id, "name": c.inventory["name"], "version": c.inventory["version"], "purl": c.inventory.get("purl", "")}
            for c in sorted(finding.components, key=lambda c: (c.inventory["name"], c.inventory["version"], c.id))
        ],
    }


def valid_cvss_rating(rating: dict) -> dict | None:
    """Accept finite CVSS scores, preserving the declared or vector-derived method."""
    method = rating.get("method", "")
    vector = rating.get("vector", "")
    if not method:
        method = next(
            (m for prefix, m in (("CVSS:4.0/", "CVSSv4"), ("CVSS:3.1/", "CVSSv31"), ("CVSS:3.0/", "CVSSv3")) if vector.startswith(prefix)),
            "",
        )
    if method not in ("CVSSv2", "CVSSv3", "CVSSv31", "CVSSv4") or isinstance(rating.get("score"), bool):
        return None
    try:
        score = float(rating["score"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"score": score, "method": method, "vector": vector} if isfinite(score) and 0 <= score <= 10 else None


def finding_cvss_ratings(finding: AssetSbomFinding) -> list[dict]:
    """Keep each rating tied to the components named by its source record."""
    references = {o["reference"]: c.id for c in finding.components for o in c.inventory["occurrences"]}
    ratings = []
    for record in finding.details["records"]:
        component_ids = sorted({references[a["ref"]] for a in record.get("affects", []) if a["ref"] in references})
        if not component_ids:
            continue
        for rating in record.get("ratings", []):
            if validated := valid_cvss_rating(rating):
                ratings.append(
                    {
                        **validated,
                        "source": rating.get("source") or record.get("source") or {},
                        "component_ids": component_ids,
                    }
                )
    return ratings
