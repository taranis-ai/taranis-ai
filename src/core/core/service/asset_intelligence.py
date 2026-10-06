"""Explainable product mentions; these matches never create vulnerability findings."""

import re
from datetime import timedelta
from functools import lru_cache
from html.parser import HTMLParser

from cpe.cpe2_3_fs import CPE2_3_FS
from cpe.cpe2_3_uri import CPE2_3_URI
from sqlalchemy.orm import selectinload

from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User


ARTICLES_PER_BATCH = 200
STORIES_PER_PAGE = 20


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


@lru_cache(maxsize=4096)
def phrase_pattern(phrase: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(word) for word in phrase.split()) + r"(?!\w)", re.IGNORECASE)


def trigger_suggestions(inventory: dict) -> list[dict]:
    suggestions: dict[str, dict] = {}

    def suggest(phrase, source):
        phrase = " ".join(phrase.split())[:200]
        if not phrase or phrase in ("*", "-"):
            return
        row = suggestions.setdefault(phrase.casefold(), {"phrase": phrase, "sources": [], "context": [], "enabled": False})
        if source not in row["sources"]:
            row["sources"].append(source)
        if phrase.casefold() == "requests" and inventory.get("purl", "").startswith("pkg:pypi/"):
            row["context"] = ["Python"]

    suggest(inventory["name"], "sbom")
    for cpe in inventory["cpes"]:
        parsed = CPE2_3_FS(cpe) if cpe.startswith("cpe:2.3:") else CPE2_3_URI(cpe)
        for product in parsed.get_product():
            suggest(re.sub(r"\\(.)", r"\1", product).replace("_", " "), "cpe")
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
            db.session.add(AssetTrigger(component.id, suggestion["phrase"], suggestion["context"], suggestion["sources"], suggestion=key))
            added += 1
    return added


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
        story = stories.setdefault(item.story_id, {"id": item.story_id, "title": item.story.title, "reasons": []})
        component = trigger.component.inventory
        story["reasons"].append(
            {
                "trigger_id": trigger.id,
                "phrase": trigger.phrase,
                "component": component["name"],
                "version": component["version"],
                "news_item_id": item.id,
                "article_title": item.title,
                "evidence": evidence,
            }
        )
        if len(stories) > page * STORIES_PER_PAGE:
            break
    return {
        "items": list(stories.values())[(page - 1) * STORIES_PER_PAGE : page * STORIES_PER_PAGE],
        "page": page,
        "has_more": len(stories) > page * STORIES_PER_PAGE,
    }
