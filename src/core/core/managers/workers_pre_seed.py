parameters = [
    {
        "description": "Full url for RSS feed",
        "name": "Feed URL",
        "key": "FEED_URL",
        "type": "STRING",
    },
    {
        "description": "Type of user agent",
        "name": "User agent",
        "key": "USER_AGENT",
        "type": "STRING",
    },
    {
        "description": "Location of the content Field",
        "name": "Content Location",
        "key": "CONTENT_LOCATION",
        "type": "STRING",
    },
    {
        "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
        "name": "Proxy server",
        "key": "PROXY_SERVER",
        "type": "STRING",
    },
    {
        "description": "How often this should be triggerd",
        "name": "Refresh interval in minutes",
        "key": "REFRESH_INTERVAL",
        "type": "NUMBER",
    },
    {
        "description": "Server type parameter means IMAP or POP3 email server",
        "name": "Email server type",
        "key": "EMAIL_SERVER_TYPE",
        "type": "STRING",
    },
    {
        "description": "Hostname of email server",
        "name": "Email server hostname",
        "key": "EMAIL_SERVER_HOSTNAME",
        "type": "STRING",
    },
    {
        "description": "Port of email server",
        "name": "Email server port",
        "key": "EMAIL_SERVER_PORT",
        "type": "NUMBER",
    },
    {
        "description": "Username of email account",
        "name": "Username",
        "key": "EMAIL_USERNAME",
        "type": "STRING",
    },
    {
        "description": "Password of email account",
        "name": "Password",
        "key": "EMAIL_PASSWORD",
        "type": "STRING",
    },
    {
        "description": "API token for Slack authentication.",
        "name": "Slack API token",
        "key": "SLACK_API_TOKEN",
        "type": "STRING",
    },
    {
        "description": "Channels which will be collected.",
        "name": "Collected workspaces channels ID",
        "key": "WORKSPACE_CHANNELS_ID",
        "type": "STRING",
    },
    {
        "description": "API key of Twitter account",
        "name": "Twitter API key",
        "key": "TWITTER_API_KEY",
        "type": "STRING",
    },
    {
        "description": "API key secret of Twitter account",
        "name": "Twitter API key secret",
        "key": "TWITTER_API_KEY_SECRET",
        "type": "STRING",
    },
    {
        "description": "Twitter access token of Twitter account",
        "name": "Twitter access token",
        "key": "TWITTER_ACCESS_TOKEN",
        "type": "STRING",
    },
    {
        "description": "Twitter access token secret of Twitter account",
        "name": "Twitter access token secret",
        "key": "TWITTER_ACCESS_TOKEN_SECRET",
        "type": "STRING",
    },
    {
        "description": "Search tweets bykeywords",
        "name": "Search by keywords",
        "key": "SEARCH_KEYWORDS",
        "type": "STRING",
    },
    {
        "description": "Search tweets by hashtags",
        "name": "Search by hashtags",
        "key": "SEARCH_HASHTAGS",
        "type": "STRING",
    },
    {
        "description": "How many tweets will be provided",
        "name": "Number of tweets",
        "key": "NUMBER_OF_TWEETS",
        "type": "NUMBER",
    },
    {
        "description": "Full url for web pageor folder of html file",
        "name": "Web URL",
        "key": "WEB_URL",
        "type": "STRING",
    },
    {
        "description": "Name of webdriver for Selenium (chrome|firefox)",
        "name": "Name of Webdriver",
        "key": "WEBDRIVER",
        "type": "STRING",
    },
    {
        "description": "Using Tor service (yes|no)",
        "name": "Do you want to use Tor service? Enter Yes or No",
        "key": "TOR",
        "type": "STRING",
    },
    {
        "description": "Username for authentication with basic auth header",
        "name": "Username for web page authentication",
        "key": "AUTH_USERNAME",
        "type": "STRING",
    },
    {
        "description": "Password for authentication with basic auth header",
        "name": "Password for web page authentication",
        "key": "AUTH_PASSWORD",
        "type": "STRING",
    },
    {
        "description": "PATH to clients certificates directory",
        "name": "PATH to directory with clients certificates",
        "key": "CLIENT_CERT_DIR",
        "type": "STRING",
    },
    {
        "description": "This is a selector of the clickable element to close the popup",
        "name": "SELECTOR at TITLE PAGE: Popup removal",
        "key": "POPUP_CLOSE_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "This is a selector of the clickable element to load the next page",
        "name": "SELECTOR at TITLE PAGE: Next page",
        "key": "NEXT_BUTTON_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "This is a selector of the clickable element to load more content",
        "name": "SELECTOR at TITLE PAGE: Load more",
        "key": "LOAD_MORE_BUTTON_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "If pagination or progressive loading, maximum number of pages to visit. Default: 1",
        "name": "Pagination limit",
        "key": "PAGINATION_LIMIT",
        "type": "NUMBER",
    },
    {
        "description": "Selector that matches the link to the article. Matching results should contain a href attribute.",
        "name": "SELECTOR at TITLE PAGE: Links to articles",
        "key": "SINGLE_ARTICLE_LINK_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "Selector for article title",
        "name": "SELECTOR at ARTICLE: Article title",
        "key": "TITLE_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "OPTIONAL: Selector of article description or summary",
        "name": "SELECTOR at ARTICLE: short summary",
        "key": "ARTICLE_DESCRIPTION_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "Selector for the article content / text of the article",
        "name": "SELECTOR at ARTICLE: Article content",
        "key": "ARTICLE_FULL_TEXT_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "OPTIONAL: Selector to find the author of the post",
        "name": "SELECTOR at ARTICLE: Author",
        "key": "AUTHOR_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "OPTIONAL: Selector of the published date",
        "name": "SELECTOR at ARTICLE: Date published",
        "key": "PUBLISHED_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "OPTIONAL: Selector for links to article attachments",
        "name": "SELECTOR at ARTICLE: Attachment selector",
        "key": "ATTACHMENT_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "Collect only first few words of the article (perhaps for legal reasons)",
        "name": "Limit article body to this many words",
        "key": "WORD_LIMIT",
        "type": "STRING",
    },
    {
        "description": "OPTIONAL: Selector of an additional article ID",
        "name": "SELECTOR at ARTICLE: Additional ID selector",
        "key": "ADDITIONAL_ID_SELECTOR",
        "type": "STRING",
    },
    {
        "description": "Full url for Atom feed",
        "name": "Atom feed URL",
        "key": "ATOM_FEED_URL",
        "type": "STRING",
    },
    {
        "name": "Source Group",
        "key": "SOURCE_GROUP",
        "description": "OSINT Source group to inspect",
        "type": "STRING",
    },
    {
        "name": "Keywords",
        "key": "KEYWORDS",
        "description": "Keywords to Tag on seperated by ','",
        "type": "STRING",
    },
    {
        "name": "Regular Expression",
        "key": "REGULAR_EXPRESSION",
        "description": "Regular expression for items matching",
        "type": "STRING",
    },
    {
        "name": "Attribute name",
        "key": "ATTRIBUTE_NAME",
        "description": "Name of attribute for extracted data",
        "type": "STRING",
    },
    {
        "name": "language",
        "key": "LANGUAGE",
        "description": "language",
        "type": "STRING",
    },
]


collectors = [
    {
        "description": "Collector for gathering data from RSS feeds",
        "name": "RSS Collector",
        "parameters": [
            "FEED_URL",
            "USER_AGENT",
            "CONTENT_LOCATION",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "RSS_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from emails",
        "name": "EMAIL Collector",
        "parameters": [
            "EMAIL_SERVER_TYPE",
            "EMAIL_SERVER_HOSTNAME",
            "EMAIL_SERVER_PORT",
            "EMAIL_USERNAME",
            "EMAIL_PASSWORD",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "EMAIL_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Slack",
        "name": "Slack Collector",
        "parameters": [
            "SLACK_API_TOKEN",
            "WORKSPACE_CHANNELS_ID",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "SLACK_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Twitter",
        "name": "Twitter Collector",
        "parameters": [
            "TWITTER_API_KEY",
            "TWITTER_API_KEY_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "TWITTER_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from web page",
        "name": "Web Collector",
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
        "type": "WEB_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Atom feeds",
        "name": "Atom Collector",
        "parameters": [
            "ATOM_FEED_URL",
            "USER_AGENT",
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "ATOM_COLLECTOR",
    },
    {
        "description": "Collector for manual input of news items",
        "name": "Manual Collector",
        "parameters": [
            "PROXY_SERVER",
            "REFRESH_INTERVAL",
        ],
        "type": "MANUAL_COLLECTOR",
    },
]

bots = [
    {
        "type": "ANALYST_BOT",
        "name": "Analyst Bot",
        "parameter_values": [
            {
                "value": "",
                "parameter": "REGULAR_EXPRESSION",
            },
            {
                "value": "",
                "parameter": "ATTRIBUTE_NAME",
            },
            {
                "value": "",
                "parameter": "SOURCE_GROUP",
            },
            {
                "value": "",
                "parameter": "REFRESH_INTERVAL",
            },
        ],
        "description": "Bot for news items analysis",
    },
    {
        "type": "GROUPING_BOT",
        "name": "Grouping Bot",
        "parameter_values": [
            {
                "value": "",
                "parameter": "SOURCE_GROUP"
            },
            {
                "value": "",
                "parameter": "REGULAR_EXPRESSION"
            },
            {
                "value": "",
                "parameter": "REFRESH_INTERVAL"
            },
        ],
        "description": "Bot for grouping news items into aggregates",
    },
    {
        "type": "NLP_BOT",
        "name": "NLP Bot",
        "parameter_values": [
            {
                "value": "",
                "parameter": "SOURCE_GROUP"
            },
            {
                "value": "",
                "parameter": "LANGUAGE"
            },
            {
                "value": "",
                "parameter": "REFRESH_INTERVAL"
            },
        ],
        "description": "Bot for naturale language processing of news items",
    },
    {
        "type": "TAGGING_BOT",
        "name": "Tagging Bot",
        "parameter_values": [
            {
                "value": "",
                "parameter": "SOURCE_GROUP"
            },
            {
                "value": "",
                "parameter": "KEYWORDS"
            },
            {
                "value": "",
                "parameter": "REFRESH_INTERVAL"
            },
        ],
        "description": "Bot for tagging news items",
    },
]
