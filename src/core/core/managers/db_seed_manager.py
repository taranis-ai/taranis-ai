from sqlalchemy.engine import Engine
from core.log import logger
from core.config import Config
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
    from core.model.worker import WORKER_CATEGORY, WORKER_TYPES, BOT_TYPES, COLLECTOR_TYPES, PRESENTER_TYPES, PUBLISHER_TYPES
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
    from core.managers.pre_seed_data import workers, bots
    from core.model.worker import Worker
    from core.model.bot import Bot
    from core.model.settings import Settings

    pre_seed_source_groups()
    pre_seed_manual_source()
    migrate_refresh_intervals()

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
    from core.managers.pre_seed_data import workers, bots, product_types
    from core.model.product_type import ProductType
    from core.model.worker import Worker
    from core.model.bot import Bot

    for w in workers:
        Worker.add(w)

    for b in bots:
        Bot.add(b)

    for p in product_types:
        ProductType.add(p)


def pre_seed_permissions():
    from core.model.permission import Permission
    from core.managers.pre_seed_data import permissions

    Permission.add_multiple(permissions)


def pre_seed_roles():
    from core.model.role import Role, TLPLevel
    from core.model.permission import Permission

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
    from core.model.attribute import Attribute
    from core.managers.pre_seed_data import attrs_with_enum

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
    from core.model.report_item_type import ReportItemType
    from core.managers.pre_seed_data import report_types

    for report_type in report_types:
        if not ReportItemType.get_by_title(title=report_type["title"]):
            ReportItemType.add(report_type)


def pre_seed_default_user():
    from core.model.organization import Organization
    from core.model.user import User
    from core.model.role import Role

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
    from core.model.organization import Organization
    from core.model.settings import Settings

    if AssetGroup.get("default"):
        return
    if not (org := Organization.get(1)):
        return
    AssetGroup.add(
        {
            "name": "Default",
            "description": "Default group for uncategorized assets",
            "organization": org,
            "id": "default",
        }
    )

    Settings.initialize()
