workers = [
    {
        "description": "Collector for gathering data from RSS feeds",
        "name": "RSS Collector",
        "parameters": [
            {"parameter": "FEED_URL", "rules": "required"},
            {"parameter": "USER_AGENT"},
            {"parameter": "CONTENT_LOCATION"},
            {"parameter": "XPATH"},
            {"parameter": "PROXY_SERVER"},
            {"parameter": "TLP_LEVEL"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "type": "RSS_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from emails",
        "name": "EMAIL Collector",
        "parameters": [
            {"parameter": "EMAIL_SERVER_TYPE"},
            {"parameter": "EMAIL_SERVER_HOSTNAME"},
            {"parameter": "EMAIL_SERVER_PORT", "type": "number"},
            {"parameter": "EMAIL_USERNAME"},
            {"parameter": "EMAIL_PASSWORD"},
            {"parameter": "PROXY_SERVER"},
            {"parameter": "TLP_LEVEL"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "type": "EMAIL_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from a web site via python requests",
        "name": "Simple Web Collector",
        "parameters": [
            "WEB_URL",
            "USER_AGENT",
            "PROXY_SERVER",
            "XPATH",
            "TLP_LEVEL",
        ],
        "type": "SIMPLE_WEB_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from web page",
        "name": "Selenium Web Collector",
        "parameters": [
            "WEB_URL",
            "WEBDRIVER",
            "TOR",
            "USER_AGENT",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
            "AUTH_USERNAME",
            "AUTH_PASSWORD",
            "CLIENT_CERT_DIR",
            "POPUP_CLOSE_SELECTOR",
            "TITLE_SELECTOR",
            "NEXT_BUTTON_SELECTOR",
            "LOAD_MORE_BUTTON_SELECTOR",
            "PAGINATION_LIMIT",
            "ARTICLE_DESCRIPTION_SELECTOR",
            "ARTICLE_FULL_TEXT_SELECTOR",
            "SINGLE_ARTICLE_LINK_SELECTOR",
            "AUTHOR_SELECTOR",
            "PUBLISHED_SELECTOR",
            "ATTACHMENT_SELECTOR",
            "WORD_LIMIT",
            "ADDITIONAL_ID_SELECTOR",
        ],
        "type": "SELENIUM_WEB_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Request Tracker",
        "name": "RT Collector",
        "parameters": [
            "BASE_URL",
            "RT_TOKEN",
            "TLP_LEVEL",
        ],
        "type": "RT_COLLECTOR",
    },
    {
        "type": "ANALYST_BOT",
        "name": "Analyst Bot",
        "parameters": [
            {"parameter": "REGULAR_EXPRESSION"},
            {"parameter": "ATTRIBUTE_NAME"},
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for news items analysis",
    },
    {
        "type": "GROUPING_BOT",
        "name": "Grouping Bot",
        "parameters": [
            {"parameter": "REGULAR_EXPRESSION"},
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for grouping news items into aggregates",
    },
    {
        "type": "NLP_BOT",
        "name": "NLP Bot",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for naturale language processing of news items",
    },
    {
        "type": "IOC_BOT",
        "name": "IOC Bot",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for extracting indicators of compromise from news items",
    },
    {
        "type": "TAGGING_BOT",
        "name": "Tagging Bot",
        "parameters": [
            {"parameter": "KEYWORDS"},
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for tagging news items",
    },
    {
        "type": "STORY_BOT",
        "name": "Story Clustering Bot",
        "parameters": [
            {
                "parameter": "ITEM_FILTER",
            },
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for Story Clustering",
    },
    {
        "type": "SUMMARY_BOT",
        "name": "Summary generation Bot",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for summarizing news items aggregates",
    },
    {
        "type": "WORDLIST_BOT",
        "name": "Wordlist Bot",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "TAGGING_WORDLISTS", "type": "table"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for tagging news items by wordlist",
    },
    {
        "type": "PDF_PRESENTER",
        "description": "Presenter for generating PDF documents",
        "parameters": ["TEMPLATE_PATH"],
        "name": "PDF Presenter",
    },
    {
        "type": "HTML_PRESENTER",
        "name": "HTML Presenter",
        "description": "Presenter for generating html documents",
        "parameters": ["TEMPLATE_PATH"],
    },
    {
        "type": "TEXT_PRESENTER",
        "name": "TEXT Presenter",
        "description": "Presenter for generating text documents",
        "parameters": ["TEMPLATE_PATH"],
    },
    {
        "type": "JSON_PRESENTER",
        "name": "JSON Presenter",
        "description": "Presenter for generating json documents",
        "parameters": ["TEMPLATE_PATH"],
    },
    {
        "type": "FTP_PUBLISHER",
        "name": "FTP Publisher",
        "description": "Publisher for publishing to FTP server",
        "parameters": ["FTP_URL"],
    },
    {
        "type": "EMAIL_PUBLISHER",
        "name": "EMAIL Publisher",
        "description": "Publisher for publishing by email",
        "parameters": [
            {"parameter": "SMTP_SERVER_ADDRESS", "rules": "required"},
            {"parameter": "SMTP_SERVER_PORT"},
            {"parameter": "SERVER_TLS", "type": "switch"},
            {"parameter": "EMAIL_USERNAME"},
            {"parameter": "EMAIL_PASSWORD"},
            {"parameter": "EMAIL_SENDER", "rules": "email"},
            {"parameter": "EMAIL_RECIPIENT", "rules": "email"},
            {"parameter": "EMAIL_SUBJECT"},
        ],
    },
    {
        "type": "TWITTER_PUBLISHER",
        "name": "Twitter Publisher",
        "description": "Publisher for publishing to Twitter account",
        "parameters": ["TWITTER_API_KEY", "TWITTER_API_KEY_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"],
    },
    {
        "type": "WORDPRESS_PUBLISHER",
        "name": "Wordpress Publisher",
        "description": "Publisher for publishing on Wordpress webpage",
        "parameters": ["WP_URL", "WP_USER", "WP_PYTHON_APP_SECRET"],
    },
    {
        "type": "MISP_PUBLISHER",
        "name": "MISP Publisher",
        "description": "Publisher for publishing in MISP",
        "parameters": ["MISP_URL", "MISP_API_KEY"],
    },
]


bots = [
    {
        "name": "Wordlist Bot",
        "description": "Bot for tagging news items by wordlist",
        "type": "WORDLIST_BOT",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch", "value": "true"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
    },
    {
        "name": "IOC BOT",
        "description": "Bot for Tagging news items",
        "type": "IOC_BOT",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch", "value": "true"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
    },
    {
        "name": "NLP Tagging BOT",
        "description": "Bot for Tagging Items via NLP",
        "type": "NLP_BOT",
        "parameters": [
            {"parameter": "ITEM_FILTER"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch", "value": "true"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
    },
    {
        "name": "Story BOT",
        "description": "Bot for story clustering",
        "type": "STORY_BOT",
        "parameters": [
            {"parameter": "ITEM_FILTER", "value": "limit=666"},
        ],
    },
    {
        "name": "Summary BOT",
        "description": "Bot for summarizing stories",
        "type": "SUMMARY_BOT",
    },
]

report_types = [
    {
        "id": 1,
        "title": "OSINT Report",
        "description": "OSINT Report",
        "attribute_groups": [
            {
                "title": "Summary",
                "description": "Summary",
                "index": 0,
                "attribute_group_items": [
                    {"title": "Summary", "description": "Summary", "index": 0, "attribute": "Text Area"},
                    {"title": "Sector trends", "description": "Sector trends", "index": 1, "attribute": "Text Area"},
                    {"title": "Vulnerabilities trends", "description": "Vulnerabilities trends", "index": 2, "attribute": "Text Area"},
                    {"title": "Ransomware trends", "description": "Ransomware trends", "index": 3, "attribute": "Text Area"},
                    {"title": "Date published", "description": "Date published", "index": 4, "attribute": "Date"},
                    {"title": "Threat level", "description": "Threat level", "index": 5, "attribute": "MISP Event Threat Level"},
                    {"title": "TLP", "description": "Traffic Light Protocol", "index": 6, "attribute": "TLP"},
                ],
            },
            {
                "title": "Ransomware",
                "description": "Ransomware",
                "index": 1,
                "attribute_group_items": [
                    {"title": "Ransomware", "description": "Ransomware", "index": 0, "attribute": "Text"},
                    {"title": "Actor", "description": "Actor", "index": 1, "attribute": "Text"},
                    {"title": "Sector", "description": "Sector", "index": 2, "attribute": "NIS Sectors"},
                    {"title": "Comment", "description": "Comment", "index": 3, "attribute": "Text Area"},
                ],
            },
        ],
    },
    {
        "id": 2,
        "title": "Disinformation",
        "description": "Disinformation",
        "attribute_groups": [
            {
                "title": "Summary",
                "description": "Summary",
                "index": 0,
                "attribute_group_items": [
                    {"title": "Title", "description": "Disinformation campaign", "index": 0, "attribute": "Text"},
                    {"title": "Quote", "description": "Quote", "index": 1, "attribute": "Text Area"},
                    {"title": "Reach", "description": "Exposed people", "index": 2, "attribute": "Number"},
                    {"title": "Date started", "description": "Campaign started", "index": 3, "attribute": "Date"},
                    {"title": "Proof", "description": "Screenshots, ...", "index": 4, "attribute": "Attachment"},
                ],
            },
            {
                "title": "Ransomware",
                "description": "Ransomware",
                "index": 1,
                "attribute_group_items": [
                    {"title": "Ransomware", "description": "Ransomware", "index": 0, "attribute": "Text"},
                    {"title": "Actor", "description": "Actor", "index": 1, "attribute": "Text"},
                    {"title": "Sector", "description": "Sector", "index": 2, "attribute": "NIS Sectors"},
                    {"title": "Comment", "description": "Comment", "index": 3, "attribute": "Text Area"},
                ],
            },
        ],
    },
    {
        "id": 3,
        "title": "Vulnerability Report",
        "description": "Vulnerability Report",
        "attribute_groups": [
            {
                "title": "Vulnerability",
                "description": "Vulnerability",
                "index": 0,
                "attribute_group_items": [
                    {
                        "title": "CVSS",
                        "description": "Common Vulnerability Scoring System",
                        "index": 0,
                        "attribute": "CVSS",
                    },
                    {
                        "title": "TLP",
                        "description": "Traffic Light Protocol",
                        "index": 1,
                        "attribute": "TLP",
                    },
                    {
                        "title": "Confidentiality",
                        "description": "Confidentiality",
                        "index": 2,
                        "attribute": "Confidentiality",
                    },
                    {
                        "title": "Description",
                        "description": "Description",
                        "index": 3,
                        "attribute": "Text Area",
                    },
                    {
                        "title": "Exposure Date",
                        "description": "Exposure Date",
                        "index": 4,
                        "attribute": "Date",
                    },
                    {
                        "title": "Update Date",
                        "description": "Update Date",
                        "index": 5,
                        "attribute": "Date",
                    },
                    {
                        "title": "CVE",
                        "description": "CVE",
                        "index": 6,
                        "attribute": "CVE",
                    },
                    {
                        "title": "Impact",
                        "description": "Impact",
                        "index": 7,
                        "attribute": "Impact",
                    },
                    {
                        "title": "Links",
                        "description": "Links",
                        "index": 8,
                        "multiple": True,
                        "attribute": "Text",
                    },
                ],
            },
            {
                "title": "Identify and Act",
                "description": "Identify and Act",
                "index": 1,
                "attribute_group_items": [
                    {
                        "title": "Affected Systems",
                        "description": "Affected Systems",
                        "index": 0,
                        "multiple": True,
                        "attribute": "CPE",
                    },
                    {
                        "title": "IOC",
                        "description": "IOC",
                        "index": 1,
                        "multiple": True,
                        "attribute": "Text",
                    },
                    {
                        "title": "Recommendations",
                        "description": "Recommendations",
                        "index": 2,
                        "attribute": "Text Area",
                    },
                ],
            },
        ],
    },
    {
        "id": 4,
        "title": "MISP Report",
        "description": "MISP Report",
        "attribute_groups": [
            {
                "title": "Event",
                "description": "Event",
                "index": 0,
                "attribute_group_items": [
                    {"title": "Event distribution", "description": "Event distribution", "index": 0, "attribute": "Text"},
                    {"title": "Event threat level", "description": "Event threat level", "index": 1, "attribute": "Text"},
                    {"title": "Event analysis", "description": "Event analysis", "index": 2, "attribute": "Text"},
                    {"title": "Event info", "description": "Event info", "index": 3, "attribute": "Text"},
                ],
            },
            {
                "title": "Attribute",
                "description": "Attribute",
                "index": 1,
                "attribute_group_items": [
                    {"title": "Category", "description": "Category", "index": 0, "attribute": "Text"},
                    {"title": "Type", "description": "Attribute type", "index": 1, "attribute": "Text"},
                    {"title": "Distribution", "description": "Distribution", "index": 2, "attribute": "Text"},
                    {"title": "Value", "description": "Value", "index": 3, "attribute": "Text Area"},
                    {"title": "Comment", "description": "Contextual comment", "index": 4, "attribute": "Text"},
                    {"title": "First seen date", "description": "First seen date", "index": 5, "attribute": "Date"},
                    {"title": "Last seen date", "description": "Last seen date", "index": 6, "attribute": "Date"},
                ],
            },
        ],
    },
]


product_types = [
    {
        "title": "Default PDF Presenter",
        "description": "Default PDF Presenter",
        "type": "PDF_PRESENTER",
        "parameters": [
            {"parameter": "TEMPLATE_PATH", "value": "pdf_template.html"},
        ],
        "report_types": [1, 2, 3, 4],
    },
    {
        "title": "Default HTML Presenter",
        "description": "Default HTML Presenter",
        "type": "HTML_PRESENTER",
        "parameters": [
            {"parameter": "TEMPLATE_PATH", "value": "html_template.html"},
        ],
        "report_types": [1, 2, 3, 4],
    },
    {
        "title": "Default TEXT Presenter",
        "description": "Default TEXT Presenter",
        "type": "TEXT_PRESENTER",
        "parameters": [
            {"parameter": "TEMPLATE_PATH", "value": "text_template.txt"},
        ],
        "report_types": [3],
    },
    {
        "title": "Default MISP Presenter",
        "description": "Default MISP Presenter",
        "type": "JSON_PRESENTER",
        "parameters": [
            {"parameter": "TEMPLATE_PATH", "value": "misp_template.json"},
        ],
        "report_types": [4],
    },
    {
        "title": "CERT Daily Report",
        "description": "cert.at Daily Report",
        "type": "HTML_PRESENTER",
        "parameters": [
            {"parameter": "TEMPLATE_PATH", "value": "cert_at_daily_report.html"},
        ],
    },
]

word_lists = [
    {
        "name": "CVE Vendors",
        "description": "List of vendors that are known to be affected by a CVE.",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/vendors.json",
        "usage": 4,
    },
    {
        "name": "CVE Products",
        "description": "List of products that are known to be affected by a CVE.",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/products.json",
        "usage": 4,
    },
    {
        "name": "Countries",
        "description": "List of Countries",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/countries.json",
        "usage": 4,
    },
    {
        "name": "Austrian Municipalities",
        "description": "List of Austrian Municipalities",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/austrian_municipalities.json",
    },
    {
        "name": "Common Cyber Security Terms",
        "description": "List of common cyber security terms",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/common.json",
        "usage": 4,
    },
    {
        "name": "APT Groups",
        "description": "List of Advanced Persistent Threat Groups",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/apt.json",
        "usage": 4,
    },
    {
        "name": "Länder",
        "description": "Liste aller Länder",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/countries_german.json",
        "usage": 4,
    },
    {
        "name": "Internationale Organisationen",
        "description": "Wichtigsten internationalen Organisationen",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/ngos_german.json",
        "usage": 4,
    },
    {
        "name": "Unternehmen Österreich",
        "description": "Größten Unternehmen in Österreich",
        "link": "https://raw.githubusercontent.com/taranis-ai/wordlists/master/output/companies_austria.json",
        "usage": 4,
    },
]


permissions = [
    ("ADMIN_OPERATIONS", "Admin operations", "Admin operations"),
    ("ASSESS_ACCESS", "Assess access", "Access to Assess module"),
    ("ASSESS_CREATE", "Assess create", "Create news item"),
    ("ASSESS_UPDATE", "Assess update", "Update news item"),
    ("ASSESS_DELETE", "Assess delete", "Delete news item"),
    ("ANALYZE_ACCESS", "Analyze access", "Access to Analyze module"),
    ("ANALYZE_CREATE", "Analyze create", "Create report item"),
    ("ANALYZE_UPDATE", "Analyze update", "Update report item"),
    ("ANALYZE_DELETE", "Analyze delete", "Delete report item"),
    ("PUBLISH_ACCESS", "Publish access", "Access to publish module"),
    ("PUBLISH_CREATE", "Publish create", "Create product"),
    ("PUBLISH_UPDATE", "Publish update", "Update product"),
    ("PUBLISH_DELETE", "Publish delete", "Delete product"),
    ("PUBLISH_PRODUCT", "Publish product", "Publish product"),
    ("CONFIG_ACCESS", "Configuration access", "Access to Configuration module"),
    (
        "CONFIG_ORGANIZATION_ACCESS",
        "Config organizations access",
        "Access to attributes configuration",
    ),
    (
        "CONFIG_ORGANIZATION_CREATE",
        "Config organization create",
        "Create organization configuration",
    ),
    (
        "CONFIG_ORGANIZATION_UPDATE",
        "Config organization update",
        "Update organization configuration",
    ),
    (
        "CONFIG_ORGANIZATION_DELETE",
        "Config organization delete",
        "Delete organization configuration",
    ),
    ("CONFIG_USER_ACCESS", "Config users access", "Access to users configuration"),
    ("CONFIG_USER_CREATE", "Config user create", "Create user configuration"),
    ("CONFIG_USER_UPDATE", "Config user update", "Update user configuration"),
    ("CONFIG_USER_DELETE", "Config user delete", "Delete user configuration"),
    ("CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration"),
    ("CONFIG_ROLE_CREATE", "Config role create", "Create role configuration"),
    ("CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration"),
    ("CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration"),
    ("CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration"),
    ("CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration"),
    ("CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration"),
    ("CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration"),
    (
        "CONFIG_PRODUCT_TYPE_ACCESS",
        "Config product types access",
        "Access to product types configuration",
    ),
    (
        "CONFIG_PRODUCT_TYPE_CREATE",
        "Config product type create",
        "Create product type configuration",
    ),
    (
        "CONFIG_PRODUCT_TYPE_UPDATE",
        "Config product type update",
        "Update product type configuration",
    ),
    (
        "CONFIG_PRODUCT_TYPE_DELETE",
        "Config product type delete",
        "Delete product type configuration",
    ),
    (
        "CONFIG_ATTRIBUTE_ACCESS",
        "Config attributes access",
        "Access to attributes configuration",
    ),
    (
        "CONFIG_ATTRIBUTE_CREATE",
        "Config attribute create",
        "Create attribute configuration",
    ),
    (
        "CONFIG_ATTRIBUTE_UPDATE",
        "Config attribute update",
        "Update attribute configuration",
    ),
    (
        "CONFIG_ATTRIBUTE_DELETE",
        "Config attribute delete",
        "Delete attribute configuration",
    ),
    (
        "CONFIG_REPORT_TYPE_ACCESS",
        "Config report item types access",
        "Access to report item types configuration",
    ),
    (
        "CONFIG_REPORT_TYPE_CREATE",
        "Config report item type create",
        "Create report item type configuration",
    ),
    (
        "CONFIG_REPORT_TYPE_UPDATE",
        "Config report item type update",
        "Update report item type configuration",
    ),
    (
        "CONFIG_REPORT_TYPE_DELETE",
        "Config report item type delete",
        "Delete report item type configuration",
    ),
    (
        "CONFIG_WORD_LIST_ACCESS",
        "Config word lists access",
        "Access to word lists configuration",
    ),
    (
        "CONFIG_WORD_LIST_CREATE",
        "Config word list create",
        "Create word list configuration",
    ),
    (
        "CONFIG_WORD_LIST_UPDATE",
        "Config word list update",
        "Update word list configuration",
    ),
    (
        "CONFIG_WORD_LIST_DELETE",
        "Config word list delete",
        "Delete word list configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_ACCESS",
        "Config OSINT source access",
        "Access to OSINT sources configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_CREATE",
        "Config OSINT source create",
        "Create OSINT source configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_UPDATE",
        "Config OSINT source update",
        "Update OSINT source configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_DELETE",
        "Config OSINT source delete",
        "Delete OSINT source configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_GROUP_ACCESS",
        "Config OSINT source group access",
        "Access to OSINT sources groups configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_GROUP_CREATE",
        "Config OSINT source group create",
        "Create OSINT source group configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_GROUP_UPDATE",
        "Config OSINT source group update",
        "Update OSINT source group configuration",
    ),
    (
        "CONFIG_OSINT_SOURCE_GROUP_DELETE",
        "Config OSINT source group delete",
        "Delete OSINT source group configuration",
    ),
    (
        "CONFIG_PUBLISHER_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    ),
    (
        "CONFIG_PUBLISHER_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    ),
    (
        "CONFIG_PUBLISHER_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    ),
    (
        "CONFIG_PUBLISHER_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
    ),
    (
        "CONFIG_BOT_ACCESS",
        "Config bots access",
        "Access to bots configuration",
    ),
    (
        "CONFIG_BOT_CREATE",
        "Config bot create",
        "Create bot configuration",
    ),
    (
        "CONFIG_BOT_UPDATE",
        "Config bot update",
        "Update bot configuration",
    ),
    (
        "CONFIG_BOT_DELETE",
        "Config bot delete",
        "Delete bot configuration",
    ),
    (
        "CONFIG_PUBLISHER_ACCESS",
        "Config publisher presets access",
        "Access to publisher presets configuration",
    ),
    (
        "CONFIG_PUBLISHER_CREATE",
        "Config publisher preset create",
        "Create publisher preset configuration",
    ),
    (
        "CONFIG_PUBLISHER_UPDATE",
        "Config publisher preset update",
        "Update publisher preset configuration",
    ),
    (
        "CONFIG_PUBLISHER_DELETE",
        "Config publisher preset delete",
        "Delete publisher preset configuration",
    ),
    ("ASSETS_ACCESS", "Assets access", "Access to Assets"),
    (
        "ASSETS_CREATE",
        "My Assets create",
        "Creation of new Assets",
    ),
    (
        "ASSETS_CONFIG",
        "My Assets config",
        "Configuration of access and groups",
    ),
    (
        "CONFIG_WORKER_ACCESS",
        "Access to workers",
        "Access to workers configuration",
    ),
    (
        "CONFIG_API_ACCESS",
        "Config API access",
        "Access to API configuration",
    ),
]
