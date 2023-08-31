workers = [
    {
        "description": "Collector for gathering data from RSS feeds",
        "name": "RSS Collector",
        "parameters": [
            {"parameter": "FEED_URL"},
            {"parameter": "USER_AGENT"},
            {"parameter": "CONTENT_LOCATION"},
            {"parameter": "PROXY_SERVER"},
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
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "type": "EMAIL_COLLECTOR",
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
        "type": "ANALYST_BOT",
        "name": "Analyst Bot",
        "parameters": [
            {"parameter": "REGULAR_EXPRESSION"},
            {"parameter": "ATTRIBUTE_NAME"},
            {"parameter": "SOURCE_GROUP", "type": "select"},
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
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for grouping news items into aggregates",
    },
    {
        "type": "NLP_BOT",
        "name": "NLP Bot",
        "parameters": [
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for naturale language processing of news items",
    },
    {
        "type": "TAGGING_BOT",
        "name": "Tagging Bot",
        "parameters": [
            {"parameter": "KEYWORDS"},
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for tagging news items",
    },
    {
        "type": "STORY_BOT",
        "name": "Story Clustering Bot",
        "parameters": [
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for Story Clustering",
    },
    {
        "type": "SUMMARY_BOT",
        "name": "Summary generation Bot",
        "parameters": [
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for summarizing news items aggregates",
    },
    {
        "type": "WORDLIST_BOT",
        "name": "Wordlist Bot",
        "parameters": [
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "TAGGING_WORDLISTS", "type": "table"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
        "description": "Bot for tagging news items by wordlist",
    },
    {
        "type": "PDF_PRESENTER",
        "description": "Presenter for generating PDF documents",
        "parameters": ["PDF_TEMPLATE_PATH"],
        "name": "PDF Presenter",
    },
    {
        "type": "HTML_PRESENTER",
        "name": "HTML Presenter",
        "description": "Presenter for generating html documents",
        "parameters": ["HTML_TEMPLATE_PATH"],
    },
    {
        "type": "TEXT_PRESENTER",
        "name": "TEXT Presenter",
        "description": "Presenter for generating text documents",
        "parameters": ["TEXT_TEMPLATE_PATH"],
    },
    {
        "type": "MISP_PRESENTER",
        "name": "MISP Presenter",
        "description": "Presenter for generating MISP platform",
        "parameters": ["MISP_TEMPLATE_PATH"],
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
            "SMTP_SERVER",
            "SMTP_SERVER_PORT",
            "EMAIL_USERNAME",
            "EMAIL_PASSWORD",
            "EMAIL_RECIPIENT",
            "EMAIL_SUBJECT",
            "EMAIL_MESSAGE",
            "EMAIL_ENCRYPTION",
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
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch", "value": "true"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
    },
    {
        "name": "NLP BOT",
        "description": "Bot for naturale language processing of news items",
        "type": "NLP_BOT",
        "parameters": [
            {"parameter": "SOURCE_GROUP", "type": "select"},
            {"parameter": "RUN_AFTER_COLLECTOR", "type": "switch", "value": "true"},
            {"parameter": "REFRESH_INTERVAL", "type": "number"},
        ],
    },
    {
        "name": "Story BOT",
        "description": "Bot for story clustering",
        "type": "STORY_BOT",
    },
]

products = [
    {
        "title": "Default PDF Presenter",
        "description": "Default PDF Presenter",
        "type": "PDF_PRESENTER",
        "parameters": [
            {"parameter": "PDF_TEMPLATE_PATH", "value": "pdf_template.html"},
        ],
    },
    {
        "title": "Default HTML Presenter",
        "description": "Default HTML Presenter",
        "type": "HTML_PRESENTER",
        "parameters": [
            {"parameter": "HTML_TEMPLATE_PATH", "value": "html_template.html"},
        ],
    },
    {
        "title": "Default TEXT Presenter",
        "description": "Default TEXT Presenter",
        "type": "TEXT_PRESENTER",
        "parameters": [
            {"parameter": "TEXT_TEMPLATE_PATH", "value": "text_template.html"},
        ],
    },
    {
        "title": "Default MISP Presenter",
        "description": "Default MISP Presenter",
        "type": "MISP_PRESENTER",
        "parameters": [
            {"parameter": "MISP_TEMPLATE_PATH", "value": "misp_template.html"},
        ],
    },
    {
        "title": "CERT Daily Report",
        "description": "cert.at Daily Report",
        "type": "HTML_PRESENTER",
        "parameters": [
            {"parameter": "HTML_TEMPLATE_PATH", "value": "cert_at_daily_report.html"},
        ],
    },
]
