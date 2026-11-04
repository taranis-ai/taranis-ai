"""Current software mentions and CVE associations with collected intelligence."""

import hashlib
import json
import re
from datetime import timedelta
from functools import lru_cache
from html.parser import HTMLParser

from cpe.cpe2_3_fs import CPE2_3_FS
from cpe.cpe2_3_uri import CPE2_3_URI
from models.assess import AssessSearchFilters
from packageurl import PackageURL
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger, SoftwareMatchRule
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFinding, AssetSbomImport
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.organization import Organization
from core.model.story import Story
from core.model.user import User
from core.service.asset_findings import cve_tag_query


ARTICLES_PER_BATCH = 200
STORY_BATCH_SIZE = 20
# These package names also occur frequently as ordinary words or license labels.
AMBIGUOUS_PRODUCT_NAMES = {"common", "core", "data", "file", "files", "main", "mit", "test", "tests", "unknown", "update"}


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "div", "br", "li", "section", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag in ("p", "div", "li", "section", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def article_text(value: str | None) -> str:
    parser = ArticleText()
    parser.feed(value or "")
    return " ".join("".join(parser.parts).split())


@lru_cache(maxsize=32768)
def phrase_pattern(phrase: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(word) for word in phrase.split()) + r"(?!\w)", re.IGNORECASE)


def trigger_suggestions(inventory: dict) -> list[dict]:
    suggestions: dict[str, dict] = {}

    def suggest(phrase, source, *, product=False):
        phrase = " ".join(phrase.split())[:200]
        if not phrase or phrase in ("*", "-"):
            return
        row = suggestions.setdefault(phrase.casefold(), {"phrase": phrase, "sources": [], "context": [], "enabled": False})
        if source not in row["sources"]:
            row["sources"].append(source)
        if product and len(phrase) >= 3 and phrase.casefold() not in AMBIGUOUS_PRODUCT_NAMES and re.search(r"[^\W\d_]", phrase):
            row["enabled"] = True
        if phrase.casefold() == "requests" and inventory.get("purl", "").startswith("pkg:pypi/"):
            row["context"] = ["Python"]

    suggest(inventory["name"], "sbom", product="/" not in inventory["name"] and "\\" not in inventory["name"])
    if inventory.get("purl"):
        suggest(PackageURL.from_string(inventory["purl"]).name, "sbom", product=True)
    for cpe in inventory["cpes"]:
        parsed = CPE2_3_FS(cpe) if cpe.startswith("cpe:2.3:") else CPE2_3_URI(cpe)
        for product in parsed.get_product():
            suggest(re.sub(r"\\(.)", r"\1", product).replace("_", " "), "cpe", product=True)
        for vendor in parsed.get_vendor():
            suggest(re.sub(r"\\(.)", r"\1", vendor).replace("_", " "), "cpe")
    for supplier in inventory.get("suppliers", []):
        suggest(supplier, "supplier")
    return list(suggestions.values())


def accessible_asset(asset_id: str, user: User) -> Asset | None:
    asset = Asset.get(asset_id)
    return asset if asset and AssetGroup.access_allowed(user.organization, asset.asset_group_id) else None


def asset_components(asset_id: str):
    return db.select(AssetSbomComponent).join(AssetSbomImport).where(AssetSbomImport.asset_id == asset_id)


def asset_triggers(asset_id: str):
    return db.select(AssetTrigger).join(AssetSbomComponent).join(AssetSbomImport).where(AssetSbomImport.asset_id == asset_id)


def product_identity(inventory: dict) -> tuple:
    """Share review across versions of a package without merging different ecosystems."""
    if inventory.get("purl"):
        package = PackageURL.from_string(inventory["purl"])
        return inventory["type"], package.type, package.namespace, package.name
    return inventory["type"], inventory.get("group", ""), inventory["name"], tuple(inventory.get("suppliers", []))


def package_rule_key(inventory: dict) -> str:
    return hashlib.sha256(json.dumps(product_identity(inventory), ensure_ascii=False).encode()).hexdigest()


def grouped_triggers(asset_id: str, *, lock=False) -> list[list[AssetTrigger]]:
    groups: dict[tuple, list[AssetTrigger]] = {}
    query = (
        asset_triggers(asset_id)
        .join(SoftwareMatchRule)
        .options(selectinload(AssetTrigger.component))
        .order_by(SoftwareMatchRule.phrase, AssetTrigger.id)
    )
    if lock:
        query = query.with_for_update(of=AssetTrigger)
    for trigger in db.session.scalars(query):
        groups.setdefault((trigger.rule_id, trigger.enabled), []).append(trigger)
    return list(groups.values())


def lock_rule_catalog(organization_id: str) -> None:
    # Serialize first imports/aliases as well as edits; SQLite ignores FOR UPDATE.
    db.session.execute(db.update(Organization).where(Organization.id == organization_id).values(name=Organization.name))


def generate_triggers(asset_id: str, *, enable_software_matching: bool = True) -> int:
    record = db.session.scalar(db.select(AssetSbomImport).filter_by(asset_id=asset_id).with_for_update())
    if record is None:
        return 0
    lock_rule_catalog(record.organization_id)
    rules = list(db.session.scalars(db.select(SoftwareMatchRule).filter_by(organization_id=record.organization_id)))
    catalog: dict[str, dict[str, SoftwareMatchRule]] = {}
    for rule in rules:
        catalog.setdefault(rule.package_key, {})[rule.key] = rule
    known = {(t.component_id, t.rule_id) for t in db.session.scalars(asset_triggers(asset_id))}
    added = 0
    for component in db.session.scalars(asset_components(asset_id)):
        package_key = package_rule_key(component.inventory)
        package_rules = catalog.setdefault(package_key, {})
        for suggestion in trigger_suggestions(component.inventory):
            key = suggestion["phrase"].casefold()
            if key not in package_rules:
                rule = SoftwareMatchRule(
                    organization_id=record.organization_id,
                    package_key=package_key,
                    key=key,
                    phrase=suggestion["phrase"],
                    context=suggestion["context"],
                    sources=suggestion["sources"],
                    default_enabled=suggestion["enabled"],
                )
                db.session.add(rule)
                db.session.flush()
                package_rules[key] = rule
        # Include analyst aliases and reviewed phrases even when a new import has different suggestions.
        for rule in package_rules.values():
            if (component.id, rule.id) in known:
                continue
            db.session.add(AssetTrigger(component.id, rule, enabled=enable_software_matching and rule.default_enabled))
            known.add((component.id, rule.id))
            added += 1
    return added


def add_shared_rule(asset_id: str, component: AssetSbomComponent, data, organization_id: str) -> list[AssetTrigger]:
    lock_rule_catalog(organization_id)
    rule = SoftwareMatchRule(
        organization_id=organization_id,
        package_key=package_rule_key(component.inventory),
        key=f"analyst:{BaseModel.uuid7_str()}",
        phrase=data.phrase,
        context=data.context,
        sources=["analyst"],
        default_enabled=True,
    )
    db.session.add(rule)
    components = db.session.execute(
        select(AssetSbomComponent, AssetSbomImport.asset_id)
        .join(AssetSbomImport)
        .where(AssetSbomImport.organization_id == organization_id, AssetSbomImport.asset_id.is_not(None))
    ).all()
    participating_components = set(db.session.scalars(db.select(AssetTrigger.component_id).where(AssetTrigger.enabled.is_(True))))
    current = []
    for installed, installed_asset_id in components:
        if package_rule_key(installed.inventory) != rule.package_key:
            continue
        enabled = data.enabled if installed_asset_id == asset_id else installed.id in participating_components
        trigger = AssetTrigger(installed.id, rule, enabled=enabled)
        trigger.analyst_edited = installed_asset_id == asset_id
        db.session.add(trigger)
        if installed_asset_id == asset_id:
            current.append(trigger)
    return current


def start_match_run(asset_id: str, user: User, days: int = 30) -> AssetMatchRun:
    """Persist the run before enqueueing so a queue failure never loses an imported asset."""
    run = AssetMatchRun(asset_id, user.id, days)
    db.session.add(run)
    db.session.commit()
    manager = queue_manager.queue_manager
    if manager.queue_action_error() or not manager.enqueue_task(
        "misc",
        "asset_match_task",
        run.id,
        job_id=run.id,
        job_timeout=1800,
        meta={"task": "asset_match_task", "user_id": user.id, "worker_id": asset_id, "worker_type": "asset_match_task"},
    ):
        run.status, run.error = "FAILED", "Unable to queue the scan. Please try again."
        db.session.commit()
    return run


def match_evidence(trigger: AssetTrigger, fields: dict[str, str]) -> list[dict]:
    context = [phrase for phrase in trigger.rule.context if any(phrase_pattern(phrase).search(text) for text in fields.values())]
    if trigger.rule.context and not context:
        return []
    reasons = []
    for field, text in fields.items():
        if match := phrase_pattern(trigger.rule.phrase).search(text):
            reasons.append(
                {
                    "field": field,
                    "matched_text": match.group(),
                    "excerpt": text[max(0, match.start() - 80) : match.end() + 80],
                    "context": context,
                }
            )
    return reasons


def match_article(item: NewsItem, triggers: list[AssetTrigger]) -> None:
    if not triggers:
        return
    # Lock the article before replacing evidence; collection and historical scans may overlap.
    current_item = db.session.scalar(
        db.select(NewsItem).where(NewsItem.id == item.id).with_for_update().execution_options(populate_existing=True)
    )
    if current_item is None:
        return
    fields = {field: article_text(getattr(current_item, field)) for field in ("title", "content")}
    ids = [t.id for t in triggers]
    db.session.execute(db.delete(AssetArticleMatch).where(AssetArticleMatch.news_item_id == item.id, AssetArticleMatch.trigger_id.in_(ids)))
    for trigger in triggers:
        if trigger.enabled and (evidence := match_evidence(trigger, fields)):
            db.session.add(AssetArticleMatch(trigger.id, item.id, evidence))


def match_news_items(item_ids: list[str]) -> None:
    if not item_ids:
        return
    triggers = list(db.session.scalars(db.select(AssetTrigger).where(AssetTrigger.enabled.is_(True))))
    if not triggers:
        return
    for item in db.session.scalars(db.select(NewsItem).where(NewsItem.id.in_(item_ids))):
        match_article(item, triggers)


def match_story(story_id: str) -> None:
    match_news_items(list(db.session.scalars(db.select(NewsItem.id).where(NewsItem.story_id == story_id))))


def article_visible(item: NewsItem, user: User) -> bool:
    return item.tlp_level.value in user.get_highest_tlp().get_accessible_levels() and item.allowed_with_acl(user, False)


def scan_batch(run: AssetMatchRun) -> None:
    user = User.get(run.user_id)
    if not user or not {"ASSETS_CREATE", "ASSESS_ACCESS"}.issubset(user.get_permissions()) or not accessible_asset(run.asset_id, user):
        run.status, run.error = "FAILED", "Access to the asset or intelligence is no longer available."
        return
    visible = Story.visible_query(user).with_only_columns(Story.id)
    query = db.select(NewsItem).where(NewsItem.story_id.in_(visible), NewsItem.id > run.cursor, NewsItem.collected <= run.created)
    if run.days:
        query = query.where(NewsItem.collected >= run.created - timedelta(days=run.days))
    items = list(db.session.scalars(query.order_by(NewsItem.id).limit(ARTICLES_PER_BATCH)))
    triggers = list(db.session.scalars(asset_triggers(run.asset_id).where(AssetTrigger.enabled.is_(True))))
    for item in items:
        if article_visible(item, user):
            match_article(item, triggers)
            run.processed += 1
        run.cursor = item.id
    run.status = "COMPLETED" if len(items) < ARTICLES_PER_BATCH else "RUNNING"


def article_intelligence(
    matches: list[tuple[AssetArticleMatch, list[dict]]],
    findings: list[AssetSbomFinding] | None = None,
    item: NewsItem | None = None,
    allowed_component_ids: set[str] | None = None,
) -> dict:
    """Summarize packages and share excerpts without losing rule/component attribution."""
    item = item or matches[0][0].news_item
    software, excerpts = {}, {}
    for match, evidence in matches:
        trigger = match.trigger
        component = trigger.component.inventory
        identity = product_identity(component)
        package = software.setdefault(identity, {"id": trigger.component_id, "name": component["name"], "components": {}})
        package["components"][trigger.component_id] = {
            "id": trigger.component_id,
            "name": component["name"],
            "version": component["version"],
            "purl": component.get("purl", ""),
        }
        for reason in evidence:
            excerpt = excerpts.setdefault(
                (reason["field"], reason["excerpt"]), {"field": reason["field"], "excerpt": reason["excerpt"], "matches": {}}
            )
            explanation = excerpt["matches"].setdefault(
                (identity, trigger.rule.phrase, reason["matched_text"], tuple(reason["context"])),
                {
                    "software_id": package["id"],
                    "phrase": trigger.rule.phrase,
                    "matched_text": reason["matched_text"],
                    "context": reason["context"],
                    "triggers": [],
                },
            )
            explanation["triggers"].append({"id": trigger.id, "component_id": trigger.component_id, "version": component["version"]})

    cve_matches = []
    for finding in findings or []:
        component_ids = []
        for installed in finding.components:
            if allowed_component_ids is not None and installed.id not in allowed_component_ids:
                continue
            component = installed.inventory
            identity = product_identity(component)
            package = software.setdefault(identity, {"id": installed.id, "name": component["name"], "components": {}})
            package["components"][installed.id] = {
                "id": installed.id,
                "name": component["name"],
                "version": component["version"],
                "purl": component.get("purl", ""),
            }
            component_ids.append(installed.id)
        cve_matches.append({"cve_id": finding.cve_id, "finding_id": finding.id, "component_ids": sorted(component_ids)})

    phrase_component_ids = {match.trigger.component_id for match, _ in matches}
    cve_component_ids = {component_id for cve in cve_matches for component_id in cve["component_ids"]}
    for package in software.values():
        for component in package["components"].values():
            component["software_match"] = component["id"] in phrase_component_ids
            component["cve_match"] = component["id"] in cve_component_ids
        package["software_match"] = any(c["software_match"] for c in package["components"].values())
        package["cve_match"] = any(c["cve_match"] for c in package["components"].values())
        package["components"] = sorted(package["components"].values(), key=lambda component: (component["version"], component["id"]))
        package["versions"] = sorted({component["version"] for component in package["components"]})
    for excerpt in excerpts.values():
        excerpt["matches"] = list(excerpt["matches"].values())
    return {
        "id": item.id,
        "title": item.title,
        "software": list(software.values()),
        "evidence": list(excerpts.values()),
        "cve_matches": cve_matches,
    }


def matching_stories(asset_ids: list[str], user: User, filters: AssessSearchFilters, story_query: Select | None = None):
    """Read bounded story batches and yield only current, accessible evidence."""
    visible = Story.visible_query(user, story_query).with_only_columns(Story.id).order_by(None)
    query = (
        db.select(AssetArticleMatch)
        .join(AssetTrigger)
        .join(AssetSbomComponent)
        .join(AssetSbomImport)
        .join(NewsItem, AssetArticleMatch.news_item_id == NewsItem.id)
        .where(AssetSbomImport.asset_id.in_(asset_ids), AssetTrigger.enabled.is_(True), NewsItem.story_id.in_(visible))
        .options(
            selectinload(AssetArticleMatch.trigger).selectinload(AssetTrigger.component),
            selectinload(AssetArticleMatch.news_item).selectinload(NewsItem.story),
        )
        .order_by(NewsItem.story_id.desc(), NewsItem.id, AssetArticleMatch.trigger_id)
    )
    associations = cve_tag_query(asset_ids).where(NewsItem.story_id.in_(visible))
    if filters.asset_cve_ids:
        associations = associations.where(AssetSbomFinding.cve_id.in_(filters.asset_cve_ids))
    candidate_ids = associations.with_only_columns(NewsItem.story_id).distinct()
    requires_cve = bool(filters.asset_cve_ids) or filters.asset_cve_match == "yes"
    requires_cve = requires_cve or filters.asset_cvss_min is not None or filters.asset_cvss_max is not None
    if requires_cve:
        # Retain product evidence only for articles with a current CVE association.
        query = query.where(NewsItem.id.in_(associations.with_only_columns(NewsItem.id)))
    else:
        candidate_ids = candidate_ids.union(query.with_only_columns(NewsItem.story_id).order_by(None))
    candidates = candidate_ids.subquery()
    ordered_candidates = (
        db.select(candidates.c.story_id).order_by(candidates.c.story_id.desc())
        if story_query is None
        else story_query.with_only_columns(Story.id).where(Story.id.in_(db.select(candidates.c.story_id)))
    )
    # Stream IDs in the caller's order; permission and evidence checks precede pagination.
    for ids in db.session.scalars(ordered_candidates.execution_options(yield_per=STORY_BATCH_SIZE)).partitions(STORY_BATCH_SIZE):
        stories = {}
        article_fields = {}
        for match in db.session.scalars(query.where(NewsItem.story_id.in_(ids))):
            item, trigger = match.news_item, match.trigger
            if not article_visible(item, user):
                continue
            if item.id not in article_fields:
                article_fields[item.id] = {field: article_text(getattr(item, field)) for field in ("title", "content")}
            fields = article_fields[item.id]
            if evidence := match_evidence(trigger, fields):
                stories.setdefault(item.story_id, []).append((match, evidence))
        tagged_stories = {}
        for item, finding in db.session.execute(
            associations.where(NewsItem.story_id.in_(ids)).order_by(NewsItem.id, AssetSbomFinding.cve_id)
        ):
            if article_visible(item, user):
                tagged_stories.setdefault(item.story_id, []).append((item, finding))
        for story_id in ids:
            if story_id in stories or story_id in tagged_stories:
                yield stories.get(story_id, []), tagged_stories.get(story_id, [])
