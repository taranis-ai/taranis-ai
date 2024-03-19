from core.managers.log_manager import logger
from core.config import Config


def pre_seed(db):
    try:
        pre_seed_permissions()
        logger.debug("Permissions seeded")

        pre_seed_source_groups()
        logger.debug("Source groups seeded")

        pre_seed_roles()
        logger.debug("Roles seeded")

        pre_seed_default_user()
        logger.debug("Default users seeded")

        pre_seed_attributes(db)
        logger.debug("Attributes seeded")

        pre_seed_report_items(db)
        logger.debug("Report items seeded")

        pre_seed_wordlists()
        logger.debug("Wordlists seeded")

        pre_seed_workers()
        logger.debug("Workers seeded")

        pre_seed_assets()
        logger.debug("Assets seeded")

    except Exception:
        logger.exception()
        logger.critical("Pre Seed failed")


def pre_seed_source_groups():
    from core.model.osint_source import OSINTSourceGroup

    if not OSINTSourceGroup.get("default"):
        OSINTSourceGroup.add({"id": "default", "name": "Default", "description": "Default group for uncategorized sources", "default": True})


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

    for p in permissions:
        Permission.add(*p)


def pre_seed_roles():
    from core.model.role import Role
    from core.model.permission import Permission

    admin_permissions = Permission.get_all_ids()
    if not Role.filter_by_name("Admin"):
        Role.add(
            {
                "name": "Admin",
                "description": "Administrator role",
                "permissions": admin_permissions,
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


def pre_seed_attributes(db):
    from core.model.attribute import Attribute

    base_attr = {
        "name": "Text",
        "description": "Simple text box",
        "type": "STRING",
        "validator_parameter": "",
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

    for attr in attrs:
        if not Attribute.filter_by_name(attr["name"]):
            attr = {**base_attr, **attr}
            Attribute.add(attr)

    from core.managers.pre_seed_data import attrs_with_enum

    for attr in attrs_with_enum:
        if not Attribute.filter_by_name(attr["name"]):
            attr = {**base_attr, **attr}
            Attribute.create_attribute_with_enum(attr)


def pre_seed_report_items(db):
    from core.model.report_item_type import ReportItemType
    from core.managers.pre_seed_data import report_types

    for report_type in report_types:
        if not ReportItemType.get_by_title(title=report_type["title"]):
            ReportItemType.add(report_type)


def pre_seed_wordlists():
    from core.model.word_list import WordList
    from core.managers.pre_seed_data import word_lists

    for word_list in word_lists:
        if not WordList.find_by_name(name=word_list["name"]):
            WordList.add(word_list)


def pre_seed_default_user():
    from core.model.organization import Organization
    from core.model.user import User
    from core.model.role import Role

    user_count = User.get_all_json()["total_count"]
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
        admin_role = Role.filter_by_name("Admin").id
        User.add(
            {
                "username": "admin",
                "name": "Arthur Dent",
                "roles": [
                    {
                        "id": admin_role,
                    },
                ],
                "permissions": [],
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
        user_role = Role.filter_by_name("User").id
        User.add(
            {
                "username": "user",
                "name": "Terry Pratchett",
                "roles": [
                    {
                        "id": user_role,
                    },
                ],
                "permissions": [],
                "organization": {"id": 2},
                "password": Config.PRE_SEED_PASSWORD_USER,
            }
        )


def pre_seed_assets():
    from core.model.asset import AssetGroup
    from core.model.user import User

    if AssetGroup.get("default"):
        return
    users = User.get_all()
    AssetGroup.add(
        {
            "name": "Default",
            "description": "Default group for uncategorized assets",
            "organization": users[0].organization,
            "id": "default",
        }
    )
