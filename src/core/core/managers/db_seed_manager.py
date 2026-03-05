from copy import deepcopy

from sqlalchemy.engine import Engine

from core.config import Config
from core.log import logger
from core.managers.db_enum_manager import sync_enum_with_db


def pre_seed():
    try:
        pre_seed_permissions()
        logger.debug("Permissions seeded")

        pre_seed_source_groups()
        logger.debug("Source groups seeded")

        pre_seed_roles()
        logger.debug("Roles seeded")

        pre_seed_default_user()
        logger.debug("Default users seeded")

        pre_seed_attributes()
        logger.debug("Attributes seeded")

        pre_seed_report_items()
        logger.debug("Report items seeded")

        pre_seed_workers()
        logger.debug("Workers seeded")

        pre_seed_assets()
        logger.debug("Assets seeded")

        pre_seed_manual_source()
        logger.debug("Manual source seeded")

    except Exception:
        logger.exception()
        logger.critical("Pre Seed failed")


def sync_enums(db_engine: Engine):
    from models.types import BOT_TYPES, COLLECTOR_TYPES, PRESENTER_TYPES, PUBLISHER_TYPES, WORKER_CATEGORY, WORKER_TYPES

    from core.model.parameter_value import PARAMETER_TYPES

    with db_engine.connect() as connection:
        if connection.dialect.name == "sqlite":
            return
        sync_enum_with_db(enum_type=WORKER_CATEGORY, connection=connection, table_column="worker.category")
        sync_enum_with_db(enum_type=WORKER_TYPES, connection=connection, table_column="worker.type")
        sync_enum_with_db(enum_type=BOT_TYPES, connection=connection, table_column="bot.type")
        sync_enum_with_db(enum_type=COLLECTOR_TYPES, connection=connection, table_column="osint_source.type")
        sync_enum_with_db(enum_type=PRESENTER_TYPES, connection=connection, table_column="product_type.type")
        sync_enum_with_db(enum_type=PUBLISHER_TYPES, connection=connection, table_column="publisher_preset.type")
        sync_enum_with_db(enum_type=PARAMETER_TYPES, connection=connection, table_column="parameter_value.type")


def pre_seed_update(db_engine: Engine):
    from core.managers.pre_seed_data import bots, workers
    from core.model.bot import Bot
    from core.model.settings import Settings
    from core.model.worker import Worker

    pre_seed_source_groups()
    pre_seed_manual_source()
    cleanup_invalid_source_icons()
    migrate_refresh_intervals()
    migrate_use_feed_content()
    migrate_user_profiles()
    cleanup_empty_stories()
    if db_engine.dialect.name == "postgresql":
        migrate_search_indexes()

    for w in workers:
        if worker := Worker.filter_by_type(w["type"]):
            worker.update(w)
        else:
            Worker.add(w)

    for b in bots:
        bot = Bot.filter_by_type(b["type"])
        if not bot:
            Bot.add(b)

    Settings.initialize()


def cleanup_invalid_source_icons():
    from core.managers.db_manager import db
    from core.model.osint_source import OSINTSource

    sources = OSINTSource.get_all_for_collector() or []
    removed_icons = 0

    for source in sources:
        icon_bytes = getattr(source, "icon", None)
        if icon_bytes and not OSINTSource._is_valid_image(icon_bytes):
            logger.warning(f"Removing invalid icon from OSINT source {source.id}")
            source.icon = None
            removed_icons += 1

    if removed_icons:
        db.session.commit()
        logger.info(f"Removed invalid icons from {removed_icons} OSINT sources")


def migrate_search_indexes():
    from core.service.story import StoryService

    count = StoryService.update_search_vector()
    logger.info(f"Updated search indexes for {count} stories")


def cleanup_empty_stories():
    from core.service.story import StoryService

    empty_stories = StoryService.delete_stories_with_no_items()
    logger.info(f"Deleted {empty_stories} empty stories")


def migrate_user_profile(user_profile: dict, template: dict) -> dict:
    out = dict(user_profile)
    if end_of_shift := out.get("end_of_shift"):
        out["end_of_shift"] = f"{end_of_shift['hours']}:{end_of_shift['minutes']}" if isinstance(end_of_shift, dict) else end_of_shift
    for key, value in template.items():
        if key in out and isinstance(value, dict) and not isinstance(out[key], dict) or key not in out:
            out[key] = deepcopy(value)
        elif isinstance(value, dict):
            out[key] = migrate_user_profile(out[key], value)
    return out


def migrate_user_profiles():
    from core.model.user import PROFILE_TEMPLATE, User

    users = User.get_all_for_collector() or []
    for user in users:
        current = user.profile if isinstance(user.profile, dict) else {}
        updated = migrate_user_profile(current, PROFILE_TEMPLATE)
        if current != updated:
            logger.debug(f"Migrating user profile for user {user.name}")
            User.update_profile(user=user, data=updated)


def migrate_refresh_intervals():
    from core.model.osint_source import OSINTSource

    sources = OSINTSource.get_all_for_collector()

    for source in sources:
        for param in source.parameters:
            if param.parameter == "REFRESH_INTERVAL":
                try:
                    interval = int(param.value)
                except ValueError:
                    continue

                new_cron = convert_interval_to_cron(interval)
                logger.info(f"Updating OSINTSource {source.id}: {interval} minutes -> cron '{new_cron}'")
                source.update_parameters({"REFRESH_INTERVAL": new_cron})


def migrate_use_feed_content():
    from core.managers.db_manager import db
    from core.model.osint_source import OSINTSource
    from core.model.parameter_value import ParameterValue

    rss_sources = OSINTSource.get_filtered(OSINTSource.get_filter_query({"type": "rss_collector"})) or []
    updated_sources = 0
    created_parameters = 0

    for source in rss_sources:
        content_location = ParameterValue.find_by_parameter(source.parameters, "CONTENT_LOCATION")
        use_feed_content = ParameterValue.find_by_parameter(source.parameters, "USE_FEED_CONTENT")

        # Only migrate sources that haven't been migrated yet and are not a boolean
        if use_feed_content and use_feed_content.value in ["true", "false"]:
            continue

        target_value = "true" if content_location and content_location.value.strip() else "false"

        if use_feed_content:
            if use_feed_content.value != target_value:
                use_feed_content.value = target_value
                updated_sources += 1
        else:
            source.parameters.append(ParameterValue(parameter="USE_FEED_CONTENT", value=target_value, type="switch"))
            updated_sources += 1
            created_parameters += 1

    if updated_sources:
        db.session.commit()
        logger.info(f"Migrated USE_FEED_CONTENT for {updated_sources} OSINT sources ({created_parameters} parameters created)")


def convert_interval_to_cron(interval: int) -> str:
    if interval < 1:
        return "0 */8 * * *"
    elif interval < 60:
        return f"*/{interval} * * * *"
    elif interval < 1440:
        hours = interval // 60
        return "0 * * * *" if hours == 1 else f"0 */{hours} * * *"
    elif interval <= 40000:
        days = interval // 1440
        return "0 4 0 * *" if days == 1 else f"0 4 */{days} * *"
    return "0 */8 * * *"


def pre_seed_source_groups():
    from core.model.osint_source import OSINTSourceGroup

    if not OSINTSourceGroup.get("default"):
        OSINTSourceGroup.add({"id": "default", "name": "Default", "description": "Default group for uncategorized sources", "default": True})


def pre_seed_manual_source():
    from core.model.osint_source import OSINTSource

    if not OSINTSource.get("manual"):
        OSINTSource.add(
            {
                "id": "manual",
                "name": "Manual",
                "description": "Manual source",
                "type": "MANUAL_COLLECTOR",
                "parameters": [],
            }
        )


def pre_seed_workers():
    from core.managers.pre_seed_data import bots, product_types, workers
    from core.model.bot import Bot
    from core.model.product_type import ProductType
    from core.model.worker import Worker

    for w in workers:
        Worker.add(w)

    for b in bots:
        Bot.add(b)

    for p in product_types:
        ProductType.add(p)


def pre_seed_permissions():
    from core.managers.pre_seed_data import permissions
    from core.model.permission import Permission

    Permission.add_multiple(permissions)


def pre_seed_roles():
    from core.model.permission import Permission
    from core.model.role import Role, TLPLevel

    admin_permissions = Permission.get_all_ids()
    if not Role.filter_by_name("Admin"):
        Role.add(
            {
                "name": "Admin",
                "description": "Administrator role",
                "permissions": admin_permissions,
                "tlp_level": TLPLevel.RED,
            }
        )
    if not Role.filter_by_name("User"):
        default_user_permissions = [
            "ASSESS_ACCESS",
            "ASSESS_CREATE",
            "ASSESS_UPDATE",
            "ASSESS_DELETE",
            "ANALYZE_ACCESS",
            "ANALYZE_CREATE",
            "ANALYZE_UPDATE",
            "ANALYZE_DELETE",
            "BOT_EXECUTE",
            "PUBLISH_ACCESS",
            "PUBLISH_CREATE",
            "PUBLISH_UPDATE",
            "PUBLISH_DELETE",
            "PUBLISH_PRODUCT",
        ]
        Role.add(
            {
                "name": "User",
                "description": "Basic user role",
                "permissions": default_user_permissions,
            }
        )


def pre_seed_attributes():
    from core.managers.pre_seed_data import attrs_with_enum
    from core.model.attribute import Attribute

    base_attr = {
        "name": "Text",
        "description": "Simple text box",
        "type": "STRING",
    }

    attrs = [
        {"name": "Text", "description": "Simple text box", "type": "STRING"},
        {"name": "Text Area", "description": "Simple text area", "type": "TEXT"},
        {"name": "Number", "description": "Simple number box", "type": "NUMBER"},
        {"name": "TLP", "description": "Traffic Light Protocol", "type": "TLP"},
        {"name": "CPE", "description": "Common Platform Enumeration", "type": "CPE"},
        {"name": "CVSS", "description": "Common Vulnerability Scoring System", "type": "CVSS"},
        {"name": "CVE", "description": "Common Vulnerabilities and Exposures", "type": "CVE"},
        {"name": "Date", "description": "Date picker", "type": "DATE"},
        {"name": "Link", "description": "Link", "type": "LINK"},
        {"name": "Attachment", "description": "Attachment", "type": "ATTACHMENT"},
        {"name": "Rich Text", "description": "Rich Text", "type": "RICH_TEXT"},
        {"name": "Boolean", "description": "Boolean", "type": "BOOLEAN"},
        {"name": "Date Time", "description": "Date Time", "type": "DATE_TIME"},
        {"name": "Date", "description": "Date", "type": "DATE"},
        {"name": "Time", "description": "Time", "type": "TIME"},
        {"name": "Story", "description": "Story", "type": "STORY"},
    ]

    for attr in attrs + attrs_with_enum:
        if not Attribute.filter_by_name(attr["name"]):
            attr = {**base_attr, **attr}
            Attribute.add(attr)


def pre_seed_report_items():
    from core.managers.pre_seed_data import report_types
    from core.model.report_item_type import ReportItemType

    for report_type in report_types:
        if not ReportItemType.get_by_title(title=report_type["title"]):
            ReportItemType.add(report_type)


def pre_seed_default_user():
    from core.model.organization import Organization
    from core.model.role import Role
    from core.model.user import User

    user_count = User.get_filtered_count(User.get_filter_query({}))
    if user_count > 0:
        return

    admin_organization = Organization.get(1)
    if not admin_organization:
        Organization.add(
            {
                "name": "The Earth",
                "description": "Earth is the third planet from the Sun and the only astronomical object known to harbor life.",
                "address": {"street": "29 Arlington Avenue", "city": "Islington, London", "zip": "N1 7BE", "country": "United Kingdom"},
            }
        )

    if not User.find_by_name(username="admin") and not User.find_by_role_name(role_name="Admin"):
        if admin_role := Role.filter_by_name("Admin"):
            User.add(
                {
                    "username": "admin",
                    "name": "Arthur Dent",
                    "roles": [admin_role.id],
                    "organization": {"id": 1},
                    "password": Config.PRE_SEED_PASSWORD_ADMIN,
                }
            )

    if not Organization.get(2):
        Organization.add(
            {
                "name": "The Clacks",
                "description": "A network infrastructure of Semaphore Towers, that operate in a similar fashion to telegraph.",
                "address": {
                    "street": "Cherry Tree Rd",
                    "city": "Beaconsfield, Buckinghamshire",
                    "zip": "HP9 1BH",
                    "country": "United Kingdom",
                },
            }
        )

    if not User.find_by_name(username="user"):
        user_role = Role.filter_by_name("User").id  # type: ignore
        User.add(
            {
                "username": "user",
                "name": "Terry Pratchett",
                "roles": [user_role],
                "organization": {"id": 2},
                "password": Config.PRE_SEED_PASSWORD_USER,
            }
        )


def pre_seed_assets():
    from core.model.asset import AssetGroup
    from core.model.settings import Settings

    AssetGroup.get_default_group()
    Settings.initialize()
