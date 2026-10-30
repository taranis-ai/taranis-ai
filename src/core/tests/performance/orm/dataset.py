"""Deterministic domain graphs and PostgreSQL template restores outside timed calls."""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from psycopg import sql
from sqlalchemy import DateTime, case, func, select

from tests.performance.orm.instrumentation import postgres_connection
from tests.performance.orm.registry import load_manifest


def identifier(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"taranis-orm-v1/{name}"))


def article(index, child=0, *, text_bytes=512, tags=1, attributes=1, prefix="seed"):
    return {
        "id": identifier(f"{prefix}-article-{index}-{child}"),
        "title": f"ORM article {prefix} {index} {child}",
        "content": (f"Profile content {index} {child}. " * (text_bytes // 20 + 1))[:text_bytes],
        "source": "orm-profile",
        "osint_source_id": "manual",
        "link": f"https://example.invalid/{prefix}/{index}/{child}",
        "language": "en",
        "published": "2026-01-15T12:00:00",
        "collected": "2026-01-15T12:00:00",
        "tags": [{"name": f"profile-tag-{number}", "tag_type": "misc"} for number in range(tags)],
        "attributes": [{"key": f"profile-attribute-{number}", "value": str(index)} for number in range(attributes)],
    }


class Dataset:
    def __init__(self, app, uri, output):
        self.app, self.uri, self.output = app, uri, Path(output)
        self.manifest = load_manifest()
        self.profile = None
        self.ids = {}
        with postgres_connection(uri, database="postgres") as connection:
            exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = 'orm_base'").fetchone()
        if not exists:
            self._clone("orm_base", "orm_profile")

    def _clone(self, destination, source):
        from core.managers.db_manager import db

        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        with postgres_connection(self.uri, database="postgres") as connection:
            connection.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(destination)))
            connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(destination), sql.Identifier(source)))
            connection.execute(sql.SQL("COMMENT ON DATABASE {} IS 'taranis-orm-disposable-v1'").format(sql.Identifier(destination)))

    def prepare(self, profile):
        from core.managers.db_manager import db
        from core.model.asset import Asset, AssetGroup
        from core.model.attribute import Attribute, AttributeType
        from core.model.bot import Bot
        from core.model.chat import ChatConversation, ChatMessage
        from core.model.connector import Connector
        from core.model.organization import Organization
        from core.model.osint_source import OSINTSource, OSINTSourceGroup
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.publisher_preset import PublisherPreset
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType
        from core.model.role import Role
        from core.model.role_based_access import ItemType, RoleBasedAccess
        from core.model.settings import Settings
        from core.model.story import NewsItemVote, Story, StoryBookmark
        from core.model.task import Task
        from core.model.user import User
        from core.model.word_list import WordList, WordListEntry

        self._clone("orm_profile", "orm_base")
        if profile == "snapshot":
            metadata = json.loads((self.output / "snapshot.json").read_text())
            with self.app.app_context():
                self.profile = profile
                self.ids = {**self.find_ids(), **metadata["scenario_inputs"]}
                rows = self.row_counts()
            (self.output / "dataset-snapshot.json").write_text(json.dumps({"profile": profile, "rows": rows}, indent=2))
            with postgres_connection(self.uri) as connection:
                connection.execute("ANALYZE")
            self._clone("orm_sample", "orm_profile")
            return
        shape = self.manifest["profiles"][profile]
        counter = iter(range(1, 10_000_000))
        with self.app.app_context(), patch("uuid.uuid7", side_effect=lambda: uuid.UUID(identifier(f"generated-{next(counter)}"))):
            db.session.add(
                OSINTSource(
                    id=identifier("collector"),
                    name="ORM collector",
                    description="Profiling source",
                    type="rss_collector",
                    enabled=False,
                    parameters={"FEED_URL": "https://example.invalid/feed"},
                )
            )
            for bot in db.session.scalars(select(Bot)):
                if bot.type.value == "intel_owl_bot":
                    bot.parameters = {**bot.parameters, "INTEL_OWL_URL": "http://fixture.invalid", "INTEL_OWL_API_KEY": "profiling-only"}
            db.session.commit()
            endpoint, status = Settings.save_llm_endpoint(
                {
                    "name": "ORM chat",
                    "base_url": "http://fixture.invalid/v1",
                    "enabled": True,
                    "api_formats": {"chat_completions": {"model": "profile"}},
                }
            )
            if status != 200:
                raise RuntimeError("Chat provider fixture creation failed")
            Settings.update({"settings": {"llm_chat_endpoint": endpoint["id"]}})
            if shape["roots"]:
                db.session.add(Organization(id=identifier("deletable-org"), name="ORM organization without members"))
                db.session.add(Role(id=identifier("deletable-role"), name="ORM role without members"))
                db.session.commit()
            for index in range(shape["roots"]):
                org = Organization(id=identifier(f"organization-{index}"), name=f"ORM organization {index}")
                db.session.add(org)
                role = Role(id=identifier(f"role-{index}"), name=f"ORM role {index}", permissions=["ASSESS_ACCESS"])
                db.session.add(role)
                db.session.flush()
                account = User(
                    id=identifier(f"user-{index}"),
                    username=f"orm-user-{index}",
                    name=f"ORM user {index}",
                    organization=org.id,
                    roles=[role.id],
                )
                db.session.add(account)
                conversation = ChatConversation(
                    id=identifier(f"conversation-{index}"), user_id=User.find_by_name("user").id, title=f"ORM conversation {index}"
                )
                conversation.messages = [
                    ChatMessage(
                        id=identifier(f"message-{index}-{child}"),
                        role="user" if child % 2 == 0 else "assistant",
                        content="Profile message " * 40,
                    )
                    for child in range(shape["children"])
                ]
                db.session.add(conversation)
                word_list = WordList(
                    id=identifier(f"word-list-{index}"),
                    name=f"ORM word list {index}",
                    entries=[WordListEntry(f"word-{child}", id=identifier(f"entry-{index}-{child}")) for child in range(shape["children"])],
                )
                db.session.add(word_list)
                if index == 0:
                    db.session.add(WordList(id=identifier("deletable-word-list"), name="ORM deletable word list"))
                db.session.add(
                    Attribute(
                        id=identifier(f"attribute-{index}"),
                        name=f"ORM attribute {index}",
                        description="Profile attribute",
                        attribute_type=AttributeType.STRING,
                    )
                )
                db.session.add(
                    Bot(
                        id=identifier(f"bot-{index}"),
                        name=f"ORM bot {index}",
                        type="wordlist_bot",
                        parameters={"TAGGING_WORDLISTS": [word_list.id]},
                        enabled=True,
                    )
                )
                db.session.add(
                    Connector(
                        id=identifier(f"connector-{index}"),
                        name=f"ORM connector {index}",
                        description="Profile connector",
                        type="misp_connector",
                        parameters={"URL": "http://fixture.invalid", "API_KEY": "profile", "ORGANISATION_ID": "1"},
                    )
                )
                db.session.add(
                    AssetGroup(
                        id=identifier(f"asset-group-{index}"),
                        name=f"ORM asset group {index}",
                        description="Profile group",
                        organization=User.find_by_name("admin").organization_id,
                    )
                )
                source = OSINTSource(
                    id=identifier(f"source-{index}"),
                    name=f"ORM source {index}",
                    description="Profile source",
                    type="rss_collector",
                    enabled=True,
                    parameters={"FEED_URL": f"https://example.invalid/feed/{index}"},
                )
                db.session.add(source)
                db.session.flush()
                source_group = OSINTSourceGroup(id=identifier(f"source-group-{index}"), name=f"ORM source group {index}")
                db.session.add(source_group)
                source_group.osint_sources = [source]
                source_group.word_lists = [word_list]
                db.session.add(
                    RoleBasedAccess(
                        id=identifier(f"acl-{index}"),
                        name=f"ORM source ACL {index}",
                        description="Profile ACL",
                        item_type=ItemType.OSINT_SOURCE,
                        item_id=source.id,
                        roles=[Role.filter_by_name("User").id],
                        read_only=index % 3 == 1,
                        enabled=True,
                    )
                )
                story_data = {
                    "id": identifier(f"story-{index}"),
                    "title": f"ORM story {index}",
                    "news_items": [
                        {
                            **article(index, child, text_bytes=shape["text_bytes"], tags=shape["tags"], attributes=shape["attributes"]),
                            "osint_source_id": source.id,
                        }
                        for child in range(shape["children"])
                    ],
                }
                result, status = Story.add(story_data)
                if status != 200:
                    raise RuntimeError("Synthetic story creation failed")
                story = Story.get(result["story_id"])
                voter = User.find_by_name("user")
                db.session.add(NewsItemVote(story.id, voter.id, like=index % 2 == 0, dislike=index % 2 == 1))
                story.likes, story.dislikes = int(index % 2 == 0), int(index % 2 == 1)
                for revision in range(shape.get("revisions", 1) - 1):
                    story.comments = f"Profile history {revision}"
                    story.record_revision(voter, note="profiling fixture")
                bookmark = StoryBookmark(
                    bookmark_id=identifier(f"bookmark-{index}"),
                    name=f"ORM bookmark {index}",
                    user_id=User.find_by_name("user").id,
                    stories=[result["story_id"]],
                )
                db.session.add(bookmark)
                product_type = db.session.scalars(select(ProductType).order_by(ProductType.id)).first()
                report_type = db.session.scalars(select(ReportItemType).order_by(ReportItemType.id)).first()
                if report_type and product_type and report_type not in product_type.report_types:
                    product_type.report_types.append(report_type)
                report, status = ReportItem.add(
                    {
                        "title": f"ORM report {index}",
                        "report_item_type_id": report_type.id,
                        "stories": [result["story_id"]],
                    }
                )
                if status != 200:
                    raise RuntimeError("Synthetic report creation failed")
                asset = Asset(
                    id=identifier(f"asset-{index}"),
                    name=f"ORM asset {index}",
                    serial=str(index),
                    description="profile",
                    group=identifier(f"asset-group-{index}"),
                )
                db.session.add(asset)
                db.session.flush()
                asset.add_vulnerability(report)
                task = Task(
                    id=f"orm-job-{index}",
                    task=source.task_id,
                    status="SUCCESS",
                    user_id=voter.id,
                    worker_id=source.id,
                    worker_type="rss_collector",
                    name=f"ORM collection {index}",
                    result={"data": {}, "message": "profile"},
                )
                task.id = identifier(f"task-{index}")
                db.session.add(task)
                if product_type:
                    product = Product(title=f"ORM product {index}", product_type_id=product_type.id, report_items=[report.id])
                    product.id = identifier(f"product-{index}")
                    db.session.add(product)
                db.session.commit()
            if shape["roots"]:
                from models.types import PUBLISHER_TYPES

                db.session.add(
                    AssetGroup(
                        id=identifier("deletable-asset-group"),
                        name="ORM asset group without assets",
                        description="Profile fixture",
                        organization=User.find_by_name("admin").organization_id,
                    )
                )
                spare_report_type = ReportItemType(id=identifier("deletable-report-type"), title="ORM deletable report type")
                db.session.add(spare_report_type)
                spare_product_type = db.session.scalars(select(ProductType).order_by(ProductType.id)).first()
                if spare_product_type:
                    clone = ProductType(
                        id=identifier("deletable-product-type"),
                        title="ORM deletable product type",
                        type=spare_product_type.type,
                        description="Profile fixture",
                        parameters=spare_product_type.parameters,
                        report_types=[],
                    )
                    db.session.add(clone)
                db.session.add(
                    PublisherPreset(
                        id=identifier("deletable-publisher"),
                        name="ORM deletable publisher",
                        type=PUBLISHER_TYPES.TARANIS_PUBLISHER,
                    )
                )
                first_product = db.session.scalars(select(Product).order_by(Product.id)).first()
                if first_product:
                    db.session.add(
                        Product(
                            id=identifier("deletable-product"),
                            title="ORM deletable product",
                            product_type_id=first_product.product_type_id,
                            report_items=[],
                        )
                    )
                db.session.commit()
                ReportItem.add({"title": "ORM deletable report", "report_item_type_id": report_type.id, "stories": [result["story_id"]]})
                manual = OSINTSource.get_by_key("manual")
                db.session.add(
                    RoleBasedAccess(
                        id=identifier("manual-acl"),
                        name="ORM manual source ACL",
                        description="Profile ACL",
                        item_type=ItemType.OSINT_SOURCE,
                        item_id=manual.id,
                        roles=[Role.filter_by_name("User").id],
                        read_only=False,
                        enabled=True,
                    )
                )
                result, status = Story.add(
                    {
                        "id": identifier("free-story"),
                        "title": "ORM unassigned manual story",
                        "news_items": [
                            article(
                                0, child, prefix="free", text_bytes=shape["text_bytes"], tags=shape["tags"], attributes=shape["attributes"]
                            )
                            for child in range(shape["children"])
                        ],
                    }
                )
                if status != 200:
                    raise RuntimeError("Manual workflow fixture creation failed")
            # Clock defaults and pre-seed generated values must not change filter membership between runs.
            timestamp = datetime.fromisoformat(self.manifest["timestamp"])
            for table in db.metadata.sorted_tables:
                dates = {
                    column.name: case((column.is_not(None), timestamp), else_=None)
                    for column in table.columns
                    if isinstance(column.type, DateTime)
                }
                if dates:
                    db.session.execute(table.update().values(**dates))
            for index in range(0, shape["roots"], 2):
                db.session.execute(
                    db.update(Task)
                    .where(Task.id == identifier(f"task-{index}"))
                    .values(last_run=datetime.fromisoformat(self.manifest["historical_task_timestamp"]))
                )
            db.session.commit()
            self.profile = profile
            self.ids = self.find_ids()
            manifest = {"profile": profile, "shape": shape, "seed": self.manifest["seed"], "rows": self.row_counts()}
            (self.output / f"dataset-{profile}.json").write_text(json.dumps(manifest, indent=2))
        with postgres_connection(self.uri) as connection:
            connection.execute("ANALYZE")
        self._clone("orm_sample", "orm_profile")

    def restore(self):
        self._clone("orm_profile", "orm_sample")

    def row_counts(self):
        from core.managers.db_manager import db

        return {table.name: db.session.scalar(select(func.count()).select_from(table)) for table in db.metadata.sorted_tables}

    def find_ids(self):
        from core.managers.db_manager import db
        from core.model import (
            bot,
            connector,
            osint_source,
            product,
            product_type,
            publisher_preset,
            report_item,
            report_item_type,
            role,
            user,
        )
        from core.model.asset import Asset, AssetGroup, AssetVulnerability
        from core.model.organization import Organization
        from core.model.settings import Settings
        from core.model.story import Story
        from core.model.task import Task
        from core.model.word_list import WordList

        models = {
            "story_id": Story,
            "news_item_id": __import__("core.model.news_item", fromlist=["NewsItem"]).NewsItem,
            "organization_id": Organization,
            "word_list_id": WordList,
            "asset_id": Asset,
            "group_id": AssetGroup,
            "source_id": osint_source.OSINTSource,
            "report_item_id": report_item.ReportItem,
            "report_type_id": report_item_type.ReportItemType,
            "product_id": product.Product,
            "product_type_id": product_type.ProductType,
            "preset_id": publisher_preset.PublisherPreset,
            "bot_id": bot.Bot,
            "connector_id": connector.Connector,
            "role_id": role.Role,
            "user_id": user.User,
            "task_id": Task,
        }
        ids = {key: db.session.scalar(select(model.id).order_by(model.id).limit(1)) for key, model in models.items()}
        ids["manual"] = "manual"
        ids["collector_id"] = identifier("collector")
        ids["new_story_id"] = identifier("worker-added-story")
        ids["worker_news_id"] = identifier("worker-added-news-item")
        ids["endpoint_id"] = Settings.get_settings().get("llm_chat_endpoint")
        ids["resource_id"] = ids["source_id"]
        ids["presenter"] = ids["product_type_id"]
        ids["publisher_id"] = ids["preset_id"]
        ids["deletable_org_id"] = identifier("deletable-org") if self.manifest["profiles"].get(self.profile, {}).get("roots") else None
        ids["deletable_role_id"] = identifier("deletable-role") if self.manifest["profiles"].get(self.profile, {}).get("roots") else None
        ids["deletable_word_list_id"] = (
            identifier("deletable-word-list") if self.manifest["profiles"].get(self.profile, {}).get("roots") else None
        )
        has_roots = bool(self.manifest["profiles"].get(self.profile, {}).get("roots"))
        ids["deletable_report_type_id"] = identifier("deletable-report-type") if has_roots else None
        ids["deletable_asset_group_id"] = identifier("deletable-asset-group") if has_roots else None
        ids["deletable_product_type_id"] = identifier("deletable-product-type") if has_roots else None
        ids["deletable_preset_id"] = identifier("deletable-publisher") if has_roots else None
        ids["deletable_product_id"] = identifier("deletable-product") if has_roots else None
        ids["bookmark_id"] = identifier("bookmark-0") if self.manifest["profiles"].get(self.profile, {}).get("roots") else None
        ids["deletable_report_id"] = db.session.scalar(
            select(report_item.ReportItem.id).where(report_item.ReportItem.title == "ORM deletable report")
        )
        ids["free_story_id"] = identifier("free-story") if has_roots else None
        ids["manual_news_item_id"] = identifier("free-article-0-0") if has_roots else None
        ids["conversation_id"] = identifier("conversation-0") if has_roots else None
        for key, name in {
            "attribute_id": "attribute-0",
            "bot_id": "bot-0",
            "connector_id": "connector-0",
            "asset_group_id": "asset-group-0",
            "source_group_id": "source-group-0",
            "acl_id": "acl-0",
        }.items():
            ids[key] = identifier(name) if has_roots else None
        ids["vulnerability_id"] = db.session.scalar(select(AssetVulnerability.id).where(AssetVulnerability.asset_id == identifier("asset-0")))
        ids["missing"] = identifier("missing")
        ids["word_list_id"] = (
            identifier("word-list-0") if self.manifest["profiles"].get(self.profile, {}).get("roots") else ids["word_list_id"]
        )
        if self.manifest["profiles"].get(self.profile, {}).get("roots"):
            ids["organization_id"] = identifier("organization-0")
            ids["role_id"] = identifier("role-0")
            ids["user_id"] = identifier("user-0")
            ids["report_item_id"] = db.session.scalar(select(report_item.ReportItem.id).where(report_item.ReportItem.title == "ORM report 0"))
            ids["story_id"] = identifier("story-0")
            ids["news_item_ids"] = [item.id for item in Story.get(ids["story_id"]).ordered_news_items]
            ids["news_item_id"] = identifier("seed-article-0-0")
            ids["source_id"] = identifier("source-0")
            ids["asset_id"] = identifier("asset-0")
        elif self.profile != "snapshot":
            for key in ("organization_id", "role_id", "user_id"):
                ids[key] = None
        return ids


def validate_snapshot(path, metadata_path):
    """Only accept a prepared, sanitized archive with independently reviewable provenance."""
    metadata = json.loads(Path(metadata_path).read_text())
    required = {
        "source_revision",
        "postgres_version",
        "schema_state",
        "captured_at",
        "sanitization",
        "sanitization_changes",
        "sha256",
        "scenario_inputs",
        "identities",
    }
    if not required.issubset(metadata) or metadata.get("sanitized") is not True:
        raise ValueError("Snapshot metadata must describe an explicitly sanitized archive and its provenance")
    if not {"admin", "user"}.issubset(metadata["identities"]):
        raise ValueError("Snapshot must identify its local administrator and user accounts")
    if not str(metadata["postgres_version"]).startswith("18"):
        raise ValueError("Snapshot must come from PostgreSQL 18")
    with Path(path).open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    if digest != metadata["sha256"]:
        raise ValueError("Snapshot checksum does not match its manifest")
    return metadata
