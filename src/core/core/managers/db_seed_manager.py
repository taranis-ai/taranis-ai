from flask_sqlalchemy import SQLAlchemy
from core.managers.log_manager import logger

db = SQLAlchemy()


def pre_seed(app):
    try:
        pre_seed_permissions()
        logger.log_debug("Permissions seeded")

        pre_seed_source_groups()
        logger.log_debug("Source groups seeded")

        pre_seed_roles()
        logger.log_debug("Roles seeded")

        pre_seed_default_user()
        logger.log_debug("Default users seeded")

        pre_seed_attributes()
        logger.log_debug("Attributes seeded")

        pre_seed_report_items()
        logger.log_debug("Report items seeded")

        pre_seed_wordlists()
        logger.log_debug("Wordlists seeded")

        pre_seed_workers()
        logger.log_debug("Workers seeded")

    except Exception:
        logger.log_debug_trace()
        logger.critical("Pre Seed failed")


def pre_seed_source_groups():
    from core.model.osint_source import OSINTSourceGroup

    OSINTSourceGroup.create(group_id="default", name="Default", description="Default group for uncategorized sources", default=True)


def pre_seed_workers():
    from core.managers.workers_pre_seed import collectors, parameters, bots, presenters, publishers
    from core.model.collector import Collector
    from core.model.parameter import Parameter
    from core.model.presenter import Presenter
    from core.model.publisher import Publisher
    from core.model.bot import Bot

    for p in parameters:
        Parameter.add(p)

    for c in collectors:
        Collector.add(c)

    for b in bots:
        Bot.add(b)

    for p in presenters:
        Presenter.add(p)

    for p in publishers:
        Publisher.add(p)


def pre_seed_permissions():
    from core.model.permission import Permission

    Permission.add("ASSESS_ACCESS", "Assess access", "Access to Assess module")
    Permission.add("ASSESS_CREATE", "Assess create", "Create news item")
    Permission.add("ASSESS_UPDATE", "Assess update", "Update news item")
    Permission.add("ASSESS_DELETE", "Assess delete", "Delete news item")

    Permission.add("ANALYZE_ACCESS", "Analyze access", "Access to Analyze module")
    Permission.add("ANALYZE_CREATE", "Analyze create", "Create report item")
    Permission.add("ANALYZE_UPDATE", "Analyze update", "Update report item")
    Permission.add("ANALYZE_DELETE", "Analyze delete", "Delete report item")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")

    Permission.add("CONFIG_ACCESS", "Configuration access", "Access to Configuration module")

    Permission.add(
        "CONFIG_ORGANIZATION_ACCESS",
        "Config organizations access",
        "Access to attributes configuration",
    )
    Permission.add(
        "CONFIG_ORGANIZATION_CREATE",
        "Config organization create",
        "Create organization configuration",
    )
    Permission.add(
        "CONFIG_ORGANIZATION_UPDATE",
        "Config organization update",
        "Update organization configuration",
    )
    Permission.add(
        "CONFIG_ORGANIZATION_DELETE",
        "Config organization delete",
        "Delete organization configuration",
    )

    Permission.add("CONFIG_USER_ACCESS", "Config users access", "Access to users configuration")
    Permission.add("CONFIG_USER_CREATE", "Config user create", "Create user configuration")
    Permission.add("CONFIG_USER_UPDATE", "Config user update", "Update user configuration")
    Permission.add("CONFIG_USER_DELETE", "Config user delete", "Delete user configuration")

    Permission.add("CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration")
    Permission.add("CONFIG_ROLE_CREATE", "Config role create", "Create role configuration")
    Permission.add("CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration")
    Permission.add("CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration")

    Permission.add("CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration")
    Permission.add("CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration")
    Permission.add("CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration")
    Permission.add("CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration")

    Permission.add(
        "CONFIG_PRODUCT_TYPE_ACCESS",
        "Config product types access",
        "Access to product types configuration",
    )
    Permission.add(
        "CONFIG_PRODUCT_TYPE_CREATE",
        "Config product type create",
        "Create product type configuration",
    )
    Permission.add(
        "CONFIG_PRODUCT_TYPE_UPDATE",
        "Config product type update",
        "Update product type configuration",
    )
    Permission.add(
        "CONFIG_PRODUCT_TYPE_DELETE",
        "Config product type delete",
        "Delete product type configuration",
    )

    Permission.add(
        "CONFIG_ATTRIBUTE_ACCESS",
        "Config attributes access",
        "Access to attributes configuration",
    )
    Permission.add(
        "CONFIG_ATTRIBUTE_CREATE",
        "Config attribute create",
        "Create attribute configuration",
    )
    Permission.add(
        "CONFIG_ATTRIBUTE_UPDATE",
        "Config attribute update",
        "Update attribute configuration",
    )
    Permission.add(
        "CONFIG_ATTRIBUTE_DELETE",
        "Config attribute delete",
        "Delete attribute configuration",
    )

    Permission.add(
        "CONFIG_REPORT_TYPE_ACCESS",
        "Config report item types access",
        "Access to report item types configuration",
    )
    Permission.add(
        "CONFIG_REPORT_TYPE_CREATE",
        "Config report item type create",
        "Create report item type configuration",
    )
    Permission.add(
        "CONFIG_REPORT_TYPE_UPDATE",
        "Config report item type update",
        "Update report item type configuration",
    )
    Permission.add(
        "CONFIG_REPORT_TYPE_DELETE",
        "Config report item type delete",
        "Delete report item type configuration",
    )

    Permission.add(
        "CONFIG_WORD_LIST_ACCESS",
        "Config word lists access",
        "Access to word lists configuration",
    )
    Permission.add(
        "CONFIG_WORD_LIST_CREATE",
        "Config word list create",
        "Create word list configuration",
    )
    Permission.add(
        "CONFIG_WORD_LIST_UPDATE",
        "Config word list update",
        "Update word list configuration",
    )
    Permission.add(
        "CONFIG_WORD_LIST_DELETE",
        "Config word list delete",
        "Delete word list configuration",
    )

    Permission.add(
        "CONFIG_COLLECTORS_NODE_ACCESS",
        "Config collectors nodes access",
        "Access to collectors nodes configuration",
    )
    Permission.add(
        "CONFIG_COLLECTORS_NODE_CREATE",
        "Config collectors node create",
        "Create collectors node configuration",
    )
    Permission.add(
        "CONFIG_COLLECTORS_NODE_UPDATE",
        "Config collectors node update",
        "Update collectors node configuration",
    )
    Permission.add(
        "CONFIG_COLLECTORS_NODE_DELETE",
        "Config collectors node delete",
        "Delete collectors node configuration",
    )

    Permission.add(
        "CONFIG_OSINT_SOURCE_ACCESS",
        "Config OSINT source access",
        "Access to OSINT sources configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_CREATE",
        "Config OSINT source create",
        "Create OSINT source configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_UPDATE",
        "Config OSINT source update",
        "Update OSINT source configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_DELETE",
        "Config OSINT source delete",
        "Delete OSINT source configuration",
    )

    Permission.add(
        "CONFIG_OSINT_SOURCE_GROUP_ACCESS",
        "Config OSINT source group access",
        "Access to OSINT sources groups configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_GROUP_CREATE",
        "Config OSINT source group create",
        "Create OSINT source group configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_GROUP_UPDATE",
        "Config OSINT source group update",
        "Update OSINT source group configuration",
    )
    Permission.add(
        "CONFIG_OSINT_SOURCE_GROUP_DELETE",
        "Config OSINT source group delete",
        "Delete OSINT source group configuration",
    )

    Permission.add(
        "CONFIG_REMOTE_ACCESS_ACCESS",
        "Config remote access access",
        "Access to remote access configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_ACCESS_CREATE",
        "Config remote access create",
        "Create remote access configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_ACCESS_UPDATE",
        "Config remote access update",
        "Update remote access configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_ACCESS_DELETE",
        "Config remote access delete",
        "Delete remote access configuration",
    )

    Permission.add(
        "CONFIG_REMOTE_NODE_ACCESS",
        "Config remote nodes access",
        "Access to remote nodes configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_NODE_CREATE",
        "Config remote node create",
        "Create remote node configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_NODE_UPDATE",
        "Config remote node update",
        "Update remote node configuration",
    )
    Permission.add(
        "CONFIG_REMOTE_NODE_DELETE",
        "Config remote node delete",
        "Delete remote node configuration",
    )

    Permission.add(
        "CONFIG_PRESENTERS_NODE_ACCESS",
        "Config presenters nodes access",
        "Access to presenters nodes configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_CREATE",
        "Config presenters node create",
        "Create presenters node configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_UPDATE",
        "Config presenters node update",
        "Update presenters node configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_DELETE",
        "Config presenters node delete",
        "Delete presenters node configuration",
    )

    Permission.add(
        "CONFIG_PUBLISHERS_NODE_ACCESS",
        "Config publishers nodes access",
        "Access to publishers nodes configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_CREATE",
        "Config publishers node create",
        "Create publishers node configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_UPDATE",
        "Config publishers node update",
        "Update publishers node configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_DELETE",
        "Config publishers node delete",
        "Delete publishers node configuration",
    )

    Permission.add(
        "CONFIG_PUBLISHER_PRESET_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
    )

    Permission.add(
        "CONFIG_BOTS_NODE_ACCESS",
        "Config bots nodes access",
        "Access to bots nodes configuration",
    )
    Permission.add(
        "CONFIG_BOTS_NODE_CREATE",
        "Config bots node create",
        "Create bots node configuration",
    )
    Permission.add(
        "CONFIG_BOTS_NODE_UPDATE",
        "Config bots node update",
        "Update bots node configuration",
    )
    Permission.add(
        "CONFIG_BOTS_NODE_DELETE",
        "Config bots node delete",
        "Delete bots node configuration",
    )

    Permission.add(
        "CONFIG_PUBLISHERS_NODE_ACCESS",
        "Config publishers nodes access",
        "Access to publishers nodes configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_CREATE",
        "Config publishers node create",
        "Create publishers node configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_UPDATE",
        "Config publishers node update",
        "Update publishers node configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHERS_NODE_DELETE",
        "Config publishers node delete",
        "Delete publishers node configuration",
    )

    Permission.add(
        "CONFIG_PUBLISHER_PRESET_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_PRESET_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
    )

    Permission.add(
        "CONFIG_PRESENTERS_NODE_ACCESS",
        "Config presenters nodes access",
        "Access to presenters nodes configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_CREATE",
        "Config presenters node create",
        "Create presenters node configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_UPDATE",
        "Config presenters node update",
        "Update presenters node configuration",
    )
    Permission.add(
        "CONFIG_PRESENTERS_NODE_DELETE",
        "Config presenters node delete",
        "Delete presenters node configuration",
    )

    Permission.add("MY_ASSETS_ACCESS", "My Assets access", "Access to My Assets module")
    Permission.add(
        "MY_ASSETS_CREATE",
        "My Assets create",
        "Creation of products in My Assets module",
    )
    Permission.add(
        "MY_ASSETS_CONFIG",
        "My Assets config",
        "Configuration of access and groups in My Assets module",
    )
    Permission.add(
        "CONFIG_NODE_ACCESS",
        "Config nodes access",
        "Access to all nodes from configuration",
    )
    Permission.add(
        "CONFIG_API_ACCESS",
        "Config API access",
        "Access to API configuration",
    )


def pre_seed_roles():
    from core.model.role import Role
    from core.model.user import User  # noqa
    from core.model.organization import Organization  # noqa
    from core.model.permission import Permission

    admin_permissions = [{"id": perm.id} for perm in Permission.get_all()]
    if not Role.find(1):
        Role.add_new(
            {
                "id": "1",
                "name": "Admin",
                "description": "Administrator role",
                "permissions": admin_permissions,
            }
        )
    if not Role.find(2):
        default_user_permissions = [
            {"id": "ASSESS_ACCESS"},
            {"id": "ASSESS_CREATE"},
            {"id": "ASSESS_UPDATE"},
            {"id": "ASSESS_DELETE"},
            {"id": "ANALYZE_ACCESS"},
            {"id": "ANALYZE_CREATE"},
            {"id": "ANALYZE_UPDATE"},
            {"id": "ANALYZE_DELETE"},
            {"id": "PUBLISH_ACCESS"},
            {"id": "PUBLISH_CREATE"},
            {"id": "PUBLISH_UPDATE"},
            {"id": "PUBLISH_DELETE"},
            {"id": "PUBLISH_PRODUCT"},
        ]
        Role.add_new(
            {
                "id": "2",
                "name": "User",
                "description": "Basic user role",
                "permissions": default_user_permissions,
            }
        )


def pre_seed_attributes():
    from core.model.attribute import Attribute

    base_attr = {
        "id": -1,
        "name": "Text",
        "description": "Simple text box",
        "type": "STRING",
        "default_value": "",
        "validator": "NONE",
        "validator_parameter": "",
        "attribute_enums": [],
        "attribute_enums_total_count": 0,
    }

    if not db.session.query(Attribute).filter_by(name="Text").first():
        attr = {
            **base_attr,
            **{"name": "Text", "description": "Simple text box", "type": "STRING"},
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Text Area").first():
        attr = {
            **base_attr,
            **{"name": "Text Area", "description": "Simple text area", "type": "TEXT"},
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="TLP").first():
        attr = {
            **base_attr,
            **{
                "name": "TLP",
                "description": "Traffic Light Protocol element",
                "type": "TLP",
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CPE").first():
        attr = {
            **base_attr,
            **{
                "name": "CPE",
                "description": "Common Platform Enumeration element",
                "type": "CPE",
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CVSS").first():
        attr = {
            **base_attr,
            **{
                "name": "CVSS",
                "description": "Common Vulnerability Scoring System element",
                "type": "CVSS",
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="CVE").first():
        attr = {
            **base_attr,
            **{
                "name": "CVE",
                "description": "Common Vulnerabilities and Exposures element",
                "type": "CVE",
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Date").first():
        attr = {
            **base_attr,
            **{"name": "Date", "description": "Date picker", "type": "DATE"},
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Confidentiality").first():
        attr_enum = [
            {"index": 0, "value": "UNRESTRICTED", "description": ""},
            {"index": 1, "value": "CLASSIFIED", "description": ""},
            {"index": 2, "value": "CONFIDENTIAL", "description": ""},
            {"index": 3, "value": "SECRET", "description": ""},
            {"index": 4, "value": "TOP SECRET", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "Confidentiality",
                "description": "Radio box for confidentiality level",
                "type": "RADIO",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Impact").first():
        attr_enum = [
            {
                "index": 0,
                "value": "Malicious code execution affecting overall confidentiality, integrity, and availability of the system",
                "description": "",
            },
            {"index": 1, "value": "Malicious code execution", "description": ""},
            {"index": 2, "value": "Denial of service", "description": ""},
            {"index": 3, "value": "Privilege escalation", "description": ""},
            {"index": 4, "value": "Information exposure", "description": ""},
            {
                "index": 5,
                "value": "Unauthorized access to the system",
                "description": "",
            },
            {"index": 6, "value": "Unauthorized change in system", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "Impact",
                "description": "Combo box for impact level",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="Additional Data").first():
        attr_enum = [
            {"index": 0, "value": "For Intrusion Detection System", "description": ""},
            {"index": 1, "value": "Disable Correlation", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "Additional Data",
                "description": "Radio box for MISP additional data",
                "type": "RADIO",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Event Distribution").first():
        attr_enum = [
            {"index": 0, "value": "Your organisation only", "description": ""},
            {"index": 1, "value": "This community only", "description": ""},
            {"index": 2, "value": "Connected communities", "description": ""},
            {"index": 3, "value": "All communities", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Event Distribution",
                "description": "Combo box for MISP event distribution",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Event Threat Level").first():
        attr_enum = [
            {"index": 0, "value": "High", "description": ""},
            {"index": 1, "value": "Medium", "description": ""},
            {"index": 2, "value": "Low", "description": ""},
            {"index": 3, "value": "Undefined", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Event Threat Level",
                "description": "Combo box for MISP event threat level",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Event Analysis").first():
        attr_enum = [
            {"index": 0, "value": "Initial", "description": ""},
            {"index": 1, "value": "Ongoing", "description": ""},
            {"index": 2, "value": "Completed", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Event Analysis",
                "description": "Combo box for MISP event analysis",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Attribute Category").first():
        attr_enum = [
            {"index": 0, "value": "Internal reference", "description": ""},
            {"index": 1, "value": "Targeting data", "description": ""},
            {"index": 2, "value": "Antivirus detection", "description": ""},
            {"index": 3, "value": "Payload delivery", "description": ""},
            {"index": 4, "value": "Artifacts dropped", "description": ""},
            {"index": 5, "value": "Payload installation", "description": ""},
            {"index": 6, "value": "Persistence mechanism", "description": ""},
            {"index": 7, "value": "Network activity", "description": ""},
            {"index": 8, "value": "Payload type", "description": ""},
            {"index": 9, "value": "Attribution", "description": ""},
            {"index": 10, "value": "External analysis", "description": ""},
            {"index": 11, "value": "Financial fraud", "description": ""},
            {"index": 12, "value": "Support Tool", "description": ""},
            {"index": 13, "value": "Social network", "description": ""},
            {"index": 14, "value": "Person", "description": ""},
            {"index": 15, "value": "Other", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Attribute Category",
                "description": "Combo box for MISP attribute category",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Attribute Type").first():
        attr_enum = [
            {"index": 0, "value": "md5", "description": ""},
            {"index": 1, "value": "sha1", "description": ""},
            {"index": 2, "value": "sha256", "description": ""},
            {"index": 3, "value": "filename", "description": ""},
            {"index": 4, "value": "pbd", "description": ""},
            {"index": 5, "value": "filename|md5", "description": ""},
            {"index": 6, "value": "filename|sha1", "description": ""},
            {"index": 7, "value": "filename|sha256", "description": ""},
            {"index": 8, "value": "ip-src", "description": ""},
            {"index": 9, "value": "ip-dst", "description": ""},
            {"index": 10, "value": "hostname", "description": ""},
            {"index": 11, "value": "domain", "description": ""},
            {"index": 12, "value": "domain|ip", "description": ""},
            {"index": 13, "value": "email-src", "description": ""},
            {"index": 14, "value": "eppn", "description": ""},
            {"index": 15, "value": "email-dst", "description": ""},
            {"index": 16, "value": "email-subject", "description": ""},
            {"index": 17, "value": "email-attachment", "description": ""},
            {"index": 18, "value": "email-body", "description": ""},
            {"index": 19, "value": "float", "description": ""},
            {"index": 20, "value": "url", "description": ""},
            {"index": 21, "value": "http-method", "description": ""},
            {"index": 22, "value": "user-agent", "description": ""},
            {"index": 23, "value": "ja3-fingerprint-md5", "description": ""},
            {"index": 24, "value": "hassh-md5", "description": ""},
            {"index": 25, "value": "hasshserver-md5", "description": ""},
            {"index": 26, "value": "reg-key", "description": ""},
            {"index": 27, "value": "regkey|value", "description": ""},
            {"index": 28, "value": "AS", "description": ""},
            {"index": 29, "value": "snort", "description": ""},
            {"index": 30, "value": "bro", "description": ""},
            {"index": 31, "value": "zeek", "description": ""},
            {"index": 32, "value": "community-id", "description": ""},
            {"index": 33, "value": "pattern-in-traffic", "description": ""},
            {"index": 34, "value": "pattern-in-memory", "description": ""},
            {"index": 35, "value": "yara", "description": ""},
            {"index": 36, "value": "stix2-pattern", "description": ""},
            {"index": 37, "value": "sigma", "description": ""},
            {"index": 38, "value": "gene", "description": ""},
            {"index": 39, "value": "kusto-query", "description": ""},
            {"index": 40, "value": "mime-type", "description": ""},
            {"index": 41, "value": "identity-card-number", "description": ""},
            {"index": 42, "value": "cookie", "description": ""},
            {"index": 43, "value": "vulnerability", "description": ""},
            {"index": 44, "value": "weakness", "description": ""},
            {"index": 45, "value": "link", "description": ""},
            {"index": 46, "value": "comment", "description": ""},
            {"index": 47, "value": "text", "description": ""},
            {"index": 48, "value": "hex", "description": ""},
            {"index": 49, "value": "other", "description": ""},
            {"index": 50, "value": "named pipe", "description": ""},
            {"index": 51, "value": "mutex", "description": ""},
            {"index": 52, "value": "target-user", "description": ""},
            {"index": 53, "value": "target-email", "description": ""},
            {"index": 54, "value": "target-machine", "description": ""},
            {"index": 55, "value": "target-org", "description": ""},
            {"index": 56, "value": "target-location", "description": ""},
            {"index": 57, "value": "target-external", "description": ""},
            {"index": 58, "value": "btc", "description": ""},
            {"index": 59, "value": "dash", "description": ""},
            {"index": 60, "value": "xmr", "description": ""},
            {"index": 61, "value": "iban", "description": ""},
            {"index": 62, "value": "bic", "description": ""},
            {"index": 63, "value": "bank-account-nr", "description": ""},
            {"index": 64, "value": "aba-rtn", "description": ""},
            {"index": 65, "value": "bin", "description": ""},
            {"index": 66, "value": "cc-number", "description": ""},
            {"index": 67, "value": "prtn", "description": ""},
            {"index": 68, "value": "phone-number", "description": ""},
            {"index": 69, "value": "threat-actor", "description": ""},
            {"index": 70, "value": "campaign-name", "description": ""},
            {"index": 71, "value": "campaign-id", "description": ""},
            {"index": 72, "value": "malware-type", "description": ""},
            {"index": 73, "value": "uri", "description": ""},
            {"index": 74, "value": "authentihash", "description": ""},
            {"index": 75, "value": "ssdeep", "description": ""},
            {"index": 76, "value": "implash", "description": ""},
            {"index": 77, "value": "pahash", "description": ""},
            {"index": 78, "value": "impfuzzy", "description": ""},
            {"index": 79, "value": "sha224", "description": ""},
            {"index": 80, "value": "sha384", "description": ""},
            {"index": 81, "value": "sha512", "description": ""},
            {"index": 82, "value": "sha512/224", "description": ""},
            {"index": 83, "value": "sha512/256", "description": ""},
            {"index": 84, "value": "tlsh", "description": ""},
            {"index": 85, "value": "cdhash", "description": ""},
            {"index": 86, "value": "filename|authentihash", "description": ""},
            {"index": 87, "value": "filename|ssdeep", "description": ""},
            {"index": 88, "value": "filename|implash", "description": ""},
            {"index": 89, "value": "filename|impfuzzy", "description": ""},
            {"index": 90, "value": "filename|pehash", "description": ""},
            {"index": 91, "value": "filename|sha224", "description": ""},
            {"index": 92, "value": "filename|sha384", "description": ""},
            {"index": 93, "value": "filename|sha512", "description": ""},
            {"index": 94, "value": "filename|sha512/224", "description": ""},
            {"index": 95, "value": "filename|sha512/256", "description": ""},
            {"index": 96, "value": "filename|tlsh", "description": ""},
            {"index": 97, "value": "windows-scheduled-task", "description": ""},
            {"index": 98, "value": "windows-service-name", "description": ""},
            {"index": 99, "value": "windows-service-displayname", "description": ""},
            {"index": 100, "value": "whois-registrant-email", "description": ""},
            {"index": 101, "value": "whois-registrant-phone", "description": ""},
            {"index": 102, "value": "whois-registrant-name", "description": ""},
            {"index": 103, "value": "whois-registrant-org", "description": ""},
            {"index": 104, "value": "whois-registrar", "description": ""},
            {"index": 105, "value": "whois-creation-date", "description": ""},
            {"index": 106, "value": "x509-fingerprint-sha1", "description": ""},
            {"index": 107, "value": "x509-fingerprint-md5", "description": ""},
            {"index": 108, "value": "x509-fingerprint-sha256", "description": ""},
            {"index": 109, "value": "dns-soa-email", "description": ""},
            {"index": 110, "value": "size-in-bytes", "description": ""},
            {"index": 111, "value": "counter", "description": ""},
            {"index": 112, "value": "datetime", "description": ""},
            {"index": 113, "value": "cpe", "description": ""},
            {"index": 114, "value": "port", "description": ""},
            {"index": 115, "value": "ip-dist|port", "description": ""},
            {"index": 116, "value": "ip-src|port", "description": ""},
            {"index": 117, "value": "hostname|port", "description": ""},
            {"index": 118, "value": "mac-address", "description": ""},
            {"index": 119, "value": "mac-eui-64", "description": ""},
            {"index": 120, "value": "email-dst-display-name", "description": ""},
            {"index": 121, "value": "email-src-display-name", "description": ""},
            {"index": 122, "value": "email-header", "description": ""},
            {"index": 123, "value": "email-reply-to", "description": ""},
            {"index": 124, "value": "email-x-mailer", "description": ""},
            {"index": 125, "value": "email-mime-boundary", "description": ""},
            {"index": 126, "value": "email-thread-index", "description": ""},
            {"index": 127, "value": "email-message-id", "description": ""},
            {"index": 128, "value": "github-username", "description": ""},
            {"index": 129, "value": "github-repository", "description": ""},
            {"index": 130, "value": "githzb-organisation", "description": ""},
            {"index": 131, "value": "jabber-id", "description": ""},
            {"index": 132, "value": "twitter-id", "description": ""},
            {"index": 133, "value": "first-name", "description": ""},
            {"index": 134, "value": "middle-name", "description": ""},
            {"index": 135, "value": "last-name", "description": ""},
            {"index": 136, "value": "date-of-birth", "description": ""},
            {"index": 137, "value": "gender", "description": ""},
            {"index": 138, "value": "passport-number", "description": ""},
            {"index": 139, "value": "passport-country", "description": ""},
            {"index": 140, "value": "passport-expiration", "description": ""},
            {"index": 141, "value": "redress-number", "description": ""},
            {"index": 142, "value": "nationality", "description": ""},
            {"index": 143, "value": "visa-number", "description": ""},
            {"index": 144, "value": "issue-date-of-the-visa", "description": ""},
            {"index": 145, "value": "primary-residence", "description": ""},
            {"index": 146, "value": "country-of-residence", "description": ""},
            {"index": 147, "value": "special-service-request", "description": ""},
            {"index": 148, "value": "frequent-flyer-number", "description": ""},
            {"index": 149, "value": "travel-details", "description": ""},
            {"index": 150, "value": "payments-details", "description": ""},
            {
                "index": 151,
                "value": "place-port-of-original-embarkation",
                "description": "",
            },
            {
                "index": 152,
                "value": "passenger-name-record-locator-number",
                "description": "",
            },
            {"index": 153, "value": "mobile-application-id", "description": ""},
            {"index": 154, "value": "chrome-extension-id", "description": ""},
            {"index": 155, "value": "cortex", "description": ""},
            {"index": 156, "value": "boolean", "description": ""},
            {"index": 157, "value": "anonymised", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Attribute Type",
                "description": "Combo box for MISP attribute type",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)

    if not db.session.query(Attribute).filter_by(name="MISP Attribute Distribution").first():
        attr_enum = [
            {"index": 0, "value": "Your organisation only", "description": ""},
            {"index": 1, "value": "This community only", "description": ""},
            {"index": 2, "value": "Connected communities", "description": ""},
            {"index": 3, "value": "All communities", "description": ""},
            {"index": 4, "value": "Inherit event", "description": ""},
        ]
        attr = {
            **base_attr,
            **{
                "name": "MISP Attribute Distribution",
                "description": "Combo box for MISP attribute type",
                "type": "ENUM",
                "attribute_enums": attr_enum,
                "attribute_enums_total_count": len(attr_enum),
            },
        }
        Attribute.add_attribute(attr)


def pre_seed_report_items():
    from core.model.report_item_type import (
        ReportItemType,
        AttributeGroupItem,
        AttributeGroup,
    )
    from core.model.attribute import Attribute

    if not db.session.query(ReportItemType).filter_by(title="Vulnerability Report").first():
        cvss_item = AttributeGroupItem(
            None,
            "CVSS",
            "",
            0,
            1,
            1,
            db.session.query(Attribute).filter_by(name="CVSS").first().id,
        )
        tlp_item = AttributeGroupItem(
            None,
            "TLP",
            "",
            1,
            1,
            1,
            db.session.query(Attribute).filter_by(name="TLP").first().id,
        )
        confidentiality_item = AttributeGroupItem(
            None,
            "Confidentiality",
            "",
            2,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Confidentiality").first().id,
        )
        description_item = AttributeGroupItem(
            None,
            "Description",
            "",
            3,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text Area").first().id,
        )
        exposure_date_item = AttributeGroupItem(
            None,
            "Exposure Date",
            "",
            4,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Date").first().id,
        )
        update_date_item = AttributeGroupItem(
            None,
            "Update Date",
            "",
            5,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Date").first().id,
        )
        cve_item = AttributeGroupItem(
            None,
            "CVE",
            "",
            6,
            0,
            1000,
            db.session.query(Attribute).filter_by(name="CVE").first().id,
        )
        impact_item = AttributeGroupItem(
            None,
            "Impact",
            "",
            7,
            0,
            1000,
            db.session.query(Attribute).filter_by(name="Impact").first().id,
        )

        group1 = AttributeGroup(
            None,
            "Vulnerability",
            "",
            0,
            "",
            0,
            [
                cvss_item,
                tlp_item,
                confidentiality_item,
                description_item,
                exposure_date_item,
                update_date_item,
                cve_item,
                impact_item,
            ],
        )

        affected_systems_item = AttributeGroupItem(
            None,
            "Affected systems",
            "",
            0,
            0,
            1000,
            db.session.query(Attribute).filter_by(name="CPE").first().id,
        )
        ioc_item = AttributeGroupItem(
            None,
            "IOC",
            "",
            1,
            0,
            1000,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )
        recommendations_item = AttributeGroupItem(
            None,
            "Recommendations",
            "",
            2,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text Area").first().id,
        )
        group2 = AttributeGroup(
            None,
            "Identify and Act",
            "",
            0,
            "",
            0,
            [affected_systems_item, ioc_item, recommendations_item],
        )

        links_item = AttributeGroupItem(
            None,
            "Links",
            "",
            0,
            0,
            1000,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )
        group3 = AttributeGroup(None, "Resources", "", 0, "", 0, [links_item])
        db.session.add(group1)
        db.session.add(group2)
        db.session.add(group3)
        db.session.commit()

        report_item_type = ReportItemType(None, "Vulnerability Report", "Basic report type", [group1, group2, group3])
        db.session.add(report_item_type)
        db.session.commit()

    if not db.session.query(ReportItemType).filter_by(title="MISP Report").first():
        event_distribution = AttributeGroupItem(
            None,
            "Event distribution",
            "",
            0,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )
        event_threat_level = AttributeGroupItem(
            None,
            "Event threat level",
            "",
            1,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )
        event_analysis = AttributeGroupItem(
            None,
            "Event analysis",
            "",
            2,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )
        event_info = AttributeGroupItem(
            None,
            "Event info",
            "",
            2,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )

        group4 = AttributeGroup(None, "Event", "", None, None, 0, [event_distribution, event_threat_level, event_analysis, event_info])

        attribute_category = AttributeGroupItem(
            None,
            "Attribute category",
            "",
            0,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )

        attribute_type = AttributeGroupItem(
            None,
            "Attribute type",
            "",
            1,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )

        attribute_distribution = AttributeGroupItem(
            None,
            "Attribute distribution",
            "",
            2,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )

        attribute_value = AttributeGroupItem(
            None,
            "Attribute value",
            "",
            3,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text Area").first().id,
        )

        attribute_comment = AttributeGroupItem(
            None,
            "Attribute contextual comment",
            "",
            4,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Text").first().id,
        )

        attribute_additional_info = AttributeGroupItem(
            None,
            "Attribute additional information",
            "",
            5,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Additional Data").first().id,
        )

        attribute_first_seen = AttributeGroupItem(
            None,
            "First seen date",
            "",
            6,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Date").first().id,
        )

        attribute_last_seen = AttributeGroupItem(
            None,
            "Last seen date",
            "",
            7,
            1,
            1,
            db.session.query(Attribute).filter_by(name="Date").first().id,
        )

        group5 = AttributeGroup(
            None,
            "Attribute",
            "",
            None,
            None,
            0,
            [
                attribute_category,
                attribute_type,
                attribute_distribution,
                attribute_value,
                attribute_comment,
                attribute_additional_info,
                attribute_first_seen,
                attribute_last_seen,
            ],
        )

        db.session.add(group4)
        db.session.add(group5)
        db.session.commit()

        report_item_type = ReportItemType(None, "MISP Report", "MISP report type", [group4, group5])
        db.session.add(report_item_type)
        db.session.commit()


def pre_seed_wordlists():
    from core.model.word_list import WordList

    if not WordList.find_by_name(name="Default EN stop list"):
        WordList.add_new(
            {
                "id": -1,
                "name": "Default EN stop list",
                "description": "English stop-word list packed with the standard Taranis NG installation.",
                "link": "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/en_complete.csv",
                "entries": [],
                "use_for_stop_words": True,
            }
        )

    if not WordList.find_by_name(name="Default SK stop list"):
        WordList.add_new(
            {
                "id": -1,
                "name": "Default SK stop list",
                "description": "Slovak stop-word list packed with the standard Taranis NG installation.",
                "entries": [],
                "link": "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/sk_complete.csv",
                "use_for_stop_words": True,
            }
        )

    if not WordList.find_by_name(name="Default highlighting wordlist"):
        WordList.add_new(
            {
                "id": -1,
                "name": "Default highlighting wordlist",
                "description": "Default highlighting list packed with the standard Taranis NG installation.",
                "entries": [],
                "link": "https://raw.githubusercontent.com/SK-CERT/Taranis-NG/main/resources/wordlists/highlighting.csv",
                "use_for_stop_words": True,
            }
        )


def pre_seed_default_user():
    from werkzeug.security import generate_password_hash
    from core.model.organization import Organization
    from core.model.user import User

    admin_organization = Organization.find(1)
    if not admin_organization:
        Organization.add_new(
            {
                "id": 1,
                "name": "The Earth",
                "description": "Earth is the third planet from the Sun and the only astronomical object known to harbor life.",
                "address": {"street": "29 Arlington Avenue", "city": "Islington, London", "zip": "N1 7BE", "country": "United Kingdom"},
            }
        )

    if not User.find(username="admin"):
        User.add_new(
            {
                "id": -1,
                "username": "admin",
                "name": "Arthur Dent",
                "roles": [
                    {
                        "id": "1",
                    },
                ],
                "permissions": [],
                "organizations": [
                    {
                        "id": 1,
                    },
                ],
                "password": generate_password_hash("admin", method="sha256"),
            }
        )

    if not Organization.find(2):
        Organization.add_new(
            {
                "id": 2,
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

    if not User.find(username="user"):
        User.add_new(
            {
                "id": -1,
                "username": "user",
                "name": "Terry Pratchett",
                "roles": [
                    {
                        "id": "2",
                    },
                ],
                "permissions": [],
                "organizations": [
                    {
                        "id": 2,
                    },
                ],
                "password": generate_password_hash("user", method="sha256"),
            }
        )
