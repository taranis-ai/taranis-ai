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
        "CONFIG_PUBLISHER_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
    )

    Permission.add(
        "CONFIG_BOT_ACCESS",
        "Config bots access",
        "Access to bots configuration",
    )
    Permission.add(
        "CONFIG_BOT_CREATE",
        "Config bot create",
        "Create bot configuration",
    )
    Permission.add(
        "CONFIG_BOT_UPDATE",
        "Config bot update",
        "Update bot configuration",
    )
    Permission.add(
        "CONFIG_BOT_DELETE",
        "Config bot delete",
        "Delete bot configuration",
    )

    Permission.add(
        "CONFIG_PUBLISHER_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    )
    Permission.add(
        "CONFIG_PUBLISHER_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
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
        "CONFIG_WORKER_ACCESS",
        "Access to workers",
        "Access to workers configuration",
    )
    Permission.add(
        "CONFIG_API_ACCESS",
        "Config API access",
        "Access to API configuration",
    )


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
    ]

    for attr in attrs:
        if not Attribute.filter_by_name(attr["name"]):
            attr = {**base_attr, **attr}
            Attribute.add(attr)

    attrs_with_enum = [
        {
            "name": "Confidentiality",
            "description": "Radio box for confidentiality level",
            "type": "RADIO",
            "attribute_enums": [
                {"index": 0, "value": "UNRESTRICTED", "description": ""},
                {"index": 1, "value": "CLASSIFIED", "description": ""},
                {"index": 2, "value": "CONFIDENTIAL", "description": ""},
                {"index": 3, "value": "SECRET", "description": ""},
                {"index": 4, "value": "TOP SECRET", "description": ""},
            ],
        },
        {
            "name": "Impact",
            "description": "Combo box for impact level",
            "type": "ENUM",
            "attribute_enums": [
                {
                    "index": 0,
                    "value": "Malicious code execution affecting CIA of the system",
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
            ],
        },
        {
            "name": "MISP Event Distribution",
            "description": "Combo box for MISP event distribution",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "Your organisation only", "description": ""},
                {"index": 1, "value": "This community only", "description": ""},
                {"index": 2, "value": "Connected communities", "description": ""},
                {"index": 3, "value": "All communities", "description": ""},
            ],
        },
        {
            "name": "MISP Event Threat Level",
            "description": "Combo box for MISP event threat level",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "High", "description": ""},
                {"index": 1, "value": "Medium", "description": ""},
                {"index": 2, "value": "Low", "description": ""},
                {"index": 3, "value": "Undefined", "description": ""},
            ],
        },
        {
            "name": "MISP Event Analysis",
            "description": "Combo box for MISP event analysis",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "Initial", "description": ""},
                {"index": 1, "value": "Ongoing", "description": ""},
                {"index": 2, "value": "Completed", "description": ""},
            ],
        },
        {
            "name": "MISP Attribute Category",
            "description": "Combo box for MISP attribute category",
            "type": "ENUM",
            "attribute_enums": [
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
            ],
        },
        {
            "name": "MISP Attribute Type",
            "description": "Combo box for MISP attribute type",
            "type": "ENUM",
            "attribute_enums": [
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
            ],
        },
        {
            "name": "MISP Attribute Distribution",
            "description": "Combo box for MISP attribute type",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "Your organisation only", "description": ""},
                {"index": 1, "value": "This community only", "description": ""},
                {"index": 2, "value": "Connected communities", "description": ""},
                {"index": 3, "value": "All communities", "description": ""},
                {"index": 4, "value": "Inherit event", "description": ""},
            ],
        },
        {
            "name": "NIS Sectors",
            "description": "Combo box for NIS sectors",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "Energy", "description": ""},
                {"index": 1, "value": "Energy / Electricity", "description": ""},
                {"index": 2, "value": "Energy / Oil", "description": ""},
                {"index": 3, "value": "Energy / Gas", "description": ""},
                {"index": 4, "value": "Transport", "description": ""},
                {"index": 5, "value": "Transport / Air", "description": ""},
                {"index": 6, "value": "Transport / Rail", "description": ""},
                {"index": 7, "value": "Transport / Water", "description": ""},
                {"index": 8, "value": "Transport / Road", "description": ""},
                {"index": 9, "value": "Banking", "description": ""},
                {"index": 10, "value": "Financial market infrastructures", "description": ""},
                {"index": 11, "value": "Health", "description": ""},
                {"index": 12, "value": "Drinking water supply and distribution", "description": ""},
                {"index": 13, "value": "Digital Infrastructure", "description": ""},
                {"index": 14, "value": "public administration", "description": ""},
                {"index": 15, "value": "postal and courier services", "description": ""},
                {"index": 16, "value": "waste management", "description": ""},
                {"index": 17, "value": "food", "description": ""},
                {"index": 18, "value": "processing/manufacturing industry", "description": ""},
                {"index": 19, "value": "Digital service providers", "description": ""},
                {"index": 20, "value": "Research", "description": ""},
                {"index": 21, "value": "Other", "description": ""},
                {"index": 22, "value": "Unknown", "description": ""},
            ],
        },
        {
            "name": "Disinfo type",
            "description": "Types of disinformation",
            "type": "ENUM",
            "attribute_enums": [
                {"index": 0, "value": "Satire or parody", "description": "Presenting humorous but false stores as if they are true"},
                {"index": 1, "value": "False connection", "description": "Headlines, visuals or captions don't support the content"},
                {
                    "index": 2,
                    "value": "Misleading content",
                    "description": "Misleading use of information to frame an issue or individual",
                },
                {
                    "index": 3,
                    "value": "False context",
                    "description": "Genuine content is shared with false contextual, e.g. images taken out of context",
                },
                {
                    "index": 4,
                    "value": "Imposter content",
                    "description": "Genuine sources, e.g. news outlets or government agencies, are impersonated",
                },
                {
                    "index": 5,
                    "value": "Fabricated content",
                    "description": "Content is made up and 100% false; designed to deceive and do harm",
                },
                {
                    "index": 6,
                    "value": "Manipulated content",
                    "description": "Genuine information manipulated to deceive, e.g. deepfakes",
                },
                {"index": 7, "value": "Ukraine", "description": "Disinformation about war in Ukraine"},
                {"index": 8, "value": "COVID", "description": "Disinformation about COVID-19"},
                {"index": 9, "value": "Cybesecurity", "description": "Disinformation about Cybesecurity"},
                {"index": 10, "value": "Electronic signature", "description": "Electronic signature"},
                {"index": 11, "value": "Classified information", "description": "Classified information"},
            ],
        },
        {
            "name": "Source Reliability",
            "description": "Source Reliability",
            "type": "RADIO",
            "attribute_enums": [
                {"index": 0, "value": "Completely reliable", "description": ""},
                {"index": 1, "value": "Usually reliable", "description": ""},
                {"index": 2, "value": "Fairly reliable", "description": ""},
                {"index": 3, "value": "Not usually reliable", "description": ""},
                {"index": 4, "value": "Unreliable", "description": ""},
                {"index": 5, "value": "Reliability cannot be judged", "description": ""},
            ],
        },
        {
            "name": "Information Credibility",
            "description": "Information Credibility",
            "type": "RADIO",
            "attribute_enums": [
                {"index": 0, "value": "Confirmed by other sources", "description": ""},
                {"index": 1, "value": "Probably True", "description": ""},
                {"index": 2, "value": "Possibly True", "description": ""},
                {"index": 3, "value": "Doubtful", "description": ""},
                {"index": 4, "value": "Improbable", "description": ""},
                {"index": 5, "value": "Truth cannot be judged", "description": ""},
            ],
        },
    ]

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
