"""Explainable product mentions; these matches never create vulnerability findings."""

import re
from datetime import timedelta
from functools import lru_cache
from html.parser import HTMLParser

from cpe.cpe2_3_fs import CPE2_3_FS
from cpe.cpe2_3_uri import CPE2_3_URI
from packageurl import PackageURL
from sqlalchemy.orm import selectinload

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User


ARTICLES_PER_BATCH = 200
STORIES_PER_PAGE = 20
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
    return inventory["type"], inventory["name"], tuple(inventory.get("suppliers", []))


def trigger_group_key(trigger: AssetTrigger) -> tuple:
    # Keep previously divergent analyst decisions visible as separate groups.
    return (
        product_identity(trigger.component.inventory),
        trigger.suggestion,
        trigger.phrase,
        tuple(trigger.context),
        trigger.enabled,
    )


def grouped_triggers(asset_id: str, *, lock=False) -> list[list[AssetTrigger]]:
    groups: dict[tuple, list[AssetTrigger]] = {}
    query = asset_triggers(asset_id).options(selectinload(AssetTrigger.component)).order_by(AssetTrigger.phrase, AssetTrigger.id)
    if lock:
        query = query.with_for_update(of=AssetTrigger)
    for trigger in db.session.scalars(query):
        groups.setdefault(trigger_group_key(trigger), []).append(trigger)
    return list(groups.values())


def generate_triggers(asset_id: str) -> int:
    # Serialize suggestion generation without rewriting an analyst's saved decisions.
    record = db.session.scalar(db.select(AssetSbomImport).where(AssetSbomImport.asset_id == asset_id).with_for_update())
    if not record:
        return 0
    known = {(t.component_id, t.suggestion) for t in db.session.scalars(asset_triggers(asset_id))}
    added = 0
    for component in db.session.scalars(asset_components(asset_id)):
        for suggestion in trigger_suggestions(component.inventory):
            key = suggestion["phrase"].casefold()
            if (component.id, key) in known:
                continue
            db.session.add(
                AssetTrigger(
                    component.id,
                    suggestion["phrase"],
                    suggestion["context"],
                    suggestion["sources"],
                    suggestion=key,
                    enabled=suggestion["enabled"],
                )
            )
            added += 1
    return added


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
    context = [phrase for phrase in trigger.context if any(phrase_pattern(phrase).search(text) for text in fields.values())]
    if trigger.context and not context:
        return []
    reasons = []
    for field, text in fields.items():
        if match := phrase_pattern(trigger.phrase).search(text):
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


def article_intelligence(matches: list[tuple[AssetArticleMatch, list[dict]]]) -> dict:
    """Summarize packages and share excerpts without losing rule/component attribution."""
    item = matches[0][0].news_item
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
                (identity, trigger.phrase, reason["matched_text"], tuple(reason["context"])),
                {
                    "software_id": package["id"],
                    "phrase": trigger.phrase,
                    "matched_text": reason["matched_text"],
                    "context": reason["context"],
                    "triggers": [],
                },
            )
            explanation["triggers"].append({"id": trigger.id, "component_id": trigger.component_id, "version": component["version"]})

    for package in software.values():
        package["components"] = sorted(package["components"].values(), key=lambda component: (component["version"], component["id"]))
        package["versions"] = sorted({component["version"] for component in package["components"]})
    for excerpt in excerpts.values():
        excerpt["matches"] = list(excerpt["matches"].values())
    return {"id": item.id, "title": item.title, "software": list(software.values()), "evidence": list(excerpts.values())}


def story_intelligence(matches: list[tuple[AssetArticleMatch, list[dict]]]) -> dict:
    story = matches[0][0].news_item.story
    assert story is not None
    articles = {}
    packages = set()
    for match, evidence in matches:
        articles.setdefault(match.news_item_id, []).append((match, evidence))
        packages.add(product_identity(match.trigger.component.inventory))
    return {
        "id": story.id,
        "title": story.title,
        "software_count": len(packages),
        "articles": [article_intelligence(article_matches) for article_matches in articles.values()],
    }


def relevant_stories(asset_id: str, user: User, page: int) -> dict:
    visible = Story.visible_query(user).with_only_columns(Story.id)
    query = (
        db.select(AssetArticleMatch)
        .join(AssetTrigger)
        .join(AssetSbomComponent)
        .join(AssetSbomImport)
        .join(NewsItem, AssetArticleMatch.news_item_id == NewsItem.id)
        .where(AssetSbomImport.asset_id == asset_id, AssetTrigger.enabled.is_(True), NewsItem.story_id.in_(visible))
        .options(
            selectinload(AssetArticleMatch.trigger).selectinload(AssetTrigger.component),
            selectinload(AssetArticleMatch.news_item).selectinload(NewsItem.story),
        )
        .order_by(NewsItem.story_id.desc(), NewsItem.id, AssetArticleMatch.trigger_id)
    )
    stories = {}
    # Re-evaluate candidates against current article text before exposing stored evidence.
    # This also suppresses stale matches from edits outside collection until the next scan.
    for match in db.session.scalars(query).yield_per(200):
        item, trigger = match.news_item, match.trigger
        if not article_visible(item, user):
            continue
        fields = {field: article_text(getattr(item, field)) for field in ("title", "content")}
        if not (evidence := match_evidence(trigger, fields)):
            continue
        stories.setdefault(item.story_id, []).append((match, evidence))
        if len(stories) > page * STORIES_PER_PAGE:
            break
    return {
        "items": [story_intelligence(matches) for matches in list(stories.values())[(page - 1) * STORIES_PER_PAGE : page * STORIES_PER_PAGE]],
        "page": page,
        "has_more": len(stories) > page * STORIES_PER_PAGE,
    }
