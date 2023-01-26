collectors = [
    {
        "description": "Collector for gathering data from RSS feeds",
        "name": "RSS Collector",
        "parameters": [
            {"description": "Full url for RSS feed", "name": "Feed URL", "id": 0, "key": "FEED_URL", "type": "STRING"},
            {"description": "Type of user agent", "name": "User agent", "id": 0, "key": "USER_AGENT", "type": "STRING"},
            {
                "description": "Location of the content Field",
                "name": "Content Location",
                "id": 0,
                "key": "CONTENT_LOCATION",
                "type": "STRING",
            },
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "RSS_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from emails",
        "name": "EMAIL Collector",
        "parameters": [
            {
                "description": "Server type parameter means IMAP or POP3 email server",
                "name": "Email server type",
                "id": 0,
                "key": "EMAIL_SERVER_TYPE",
                "type": "STRING",
            },
            {
                "description": "Hostname of email server",
                "name": "Email server hostname",
                "id": 0,
                "key": "EMAIL_SERVER_HOSTNAME",
                "type": "STRING",
            },
            {"description": "Port of email server", "name": "Email server port", "id": 0, "key": "EMAIL_SERVER_PORT", "type": "NUMBER"},
            {"description": "Username of email account", "name": "Username", "id": 0, "key": "EMAIL_USERNAME", "type": "STRING"},
            {"description": "Password of email account", "name": "Password", "id": 0, "key": "EMAIL_PASSWORD", "type": "STRING"},
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "EMAIL_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Slack",
        "name": "Slack Collector",
        "parameters": [
            {
                "description": "API token for Slack authentication.",
                "name": "Slack API token",
                "id": 0,
                "key": "SLACK_API_TOKEN",
                "type": "STRING",
            },
            {
                "description": "Channels which will be collected.",
                "name": "Collected workspaces channels ID",
                "id": 0,
                "key": "WORKSPACE_CHANNELS_ID",
                "type": "STRING",
            },
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "SLACK_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Twitter",
        "name": "Twitter Collector",
        "parameters": [
            {"description": "API key of Twitter account", "name": "Twitter API key", "id": 0, "key": "TWITTER_API_KEY", "type": "STRING"},
            {
                "description": "API key secret of Twitter account",
                "name": "Twitter API key secret",
                "id": 0,
                "key": "TWITTER_API_KEY_SECRET",
                "type": "STRING",
            },
            {
                "description": "Twitter access token of Twitter account",
                "name": "Twitter access token",
                "id": 0,
                "key": "TWITTER_ACCESS_TOKEN",
                "type": "STRING",
            },
            {
                "description": "Twitter access token secret of Twitter account",
                "name": "Twitter access token secret",
                "id": 0,
                "key": "TWITTER_ACCESS_TOKEN_SECRET",
                "type": "STRING",
            },
            {"description": "Search tweets bykeywords", "name": "Search by keywords", "id": 0, "key": "SEARCH_KEYWORDS", "type": "STRING"},
            {"description": "Search tweets by hashtags", "name": "Search by hashtags", "id": 0, "key": "SEARCH_HASHTAGS", "type": "STRING"},
            {
                "description": "How many tweets will be provided",
                "name": "Number of tweets",
                "id": 0,
                "key": "NUMBER_OF_TWEETS",
                "type": "NUMBER",
            },
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "TWITTER_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from web page",
        "name": "Web Collector",
        "parameters": [
            {"description": "Full url for web pageor folder of html file", "name": "Web URL", "id": 0, "key": "WEB_URL", "type": "STRING"},
            {
                "description": "Name of webdriver for Selenium (chrome|firefox)",
                "name": "Name of Webdriver",
                "id": 0,
                "key": "WEBDRIVER",
                "type": "STRING",
            },
            {
                "description": "Using Tor service (yes|no)",
                "name": "Do you want to use Tor service? Enter Yes or No",
                "id": 0,
                "key": "TOR",
                "type": "STRING",
            },
            {"description": "Set user agent", "name": "User agent", "id": 0, "key": "USER_AGENT", "type": "STRING"},
            {
                "description": "Username for authentication with basic auth header",
                "name": "Username for web page authentication",
                "id": 0,
                "key": "AUTH_USERNAME",
                "type": "STRING",
            },
            {
                "description": "Password for authentication with basic auth header",
                "name": "Password for web page authentication",
                "id": 0,
                "key": "AUTH_PASSWORD",
                "type": "STRING",
            },
            {
                "description": "PATH to clients certificates directory",
                "name": "PATH to directory with clients certificates",
                "id": 0,
                "key": "CLIENT_CERT_DIR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: For sites with popups, this is a selector of the clickable element (button or a link) for the popup removal button",
                "name": "SELECTOR at TITLE PAGE: Popup removal",
                "id": 0,
                "key": "POPUP_CLOSE_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Forsites with pagination, this is a selector of the clickable element (button or a link) for the next page",
                "name": "SELECTOR at TITLE PAGE: Next page",
                "id": 0,
                "key": "NEXT_BUTTON_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: For sites with progressive loading, this is a selector of the clickable element (button or a link) for the load more",
                "name": "SELECTOR at TITLE PAGE: Load more",
                "id": 0,
                "key": "LOAD_MORE_BUTTON_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: For sites with pagination or progressive loading, maximum number of pages to visit. Default: 1 (stay on the first page only)",
                "name": "Pagination limit",
                "id": 0,
                "key": "PAGINATION_LIMIT",
                "type": "NUMBER",
            },
            {
                "description": "Selector that matches the link to the article. Matching results should contain a href attribute.",
                "name": "SELECTOR at TITLE PAGE: Links to articles",
                "id": 0,
                "key": "SINGLE_ARTICLE_LINK_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "Selector for article title",
                "name": "SELECTOR at ARTICLE: Article title",
                "id": 0,
                "key": "TITLE_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Selector of article description or summary",
                "name": "SELECTOR at ARTICLE: short summary",
                "id": 0,
                "key": "ARTICLE_DESCRIPTION_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "Selector for the article content / text of the article",
                "name": "SELECTOR at ARTICLE: Article content",
                "id": 0,
                "key": "ARTICLE_FULL_TEXT_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Selector to find the author of the post",
                "name": "SELECTOR at ARTICLE: Author",
                "id": 0,
                "key": "AUTHOR_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Selector of the published date",
                "name": "SELECTOR at ARTICLE: Date published",
                "id": 0,
                "key": "PUBLISHED_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Selector for links to article attachments",
                "name": "SELECTOR at ARTICLE: Attachment selector",
                "id": 0,
                "key": "ATTACHMENT_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "Collect only first few words of the article (perhaps for legal reasons)",
                "name": "Limit article body to this many words",
                "id": 0,
                "key": "WORD_LIMIT",
                "type": "STRING",
            },
            {
                "description": "OPTIONAL: Selector of an additional article ID",
                "name": "SELECTOR at ARTICLE: Additional ID selector",
                "id": 0,
                "key": "ADDITIONAL_ID_SELECTOR",
                "type": "STRING",
            },
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "WEB_COLLECTOR",
    },
    {
        "description": "Collector for gathering data from Atom feeds",
        "name": "Atom Collector",
        "parameters": [
            {"description": "Full url for Atom feed", "name": "Atom feed URL", "id": 0, "key": "ATOM_FEED_URL", "type": "STRING"},
            {"description": "Type of user agent", "name": "User agent", "id": 0, "key": "USER_AGENT", "type": "STRING"},
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "ATOM_COLLECTOR",
    },
    {
        "description": "Collector for manual input of news items",
        "name": "Manual Collector",
        "parameters": [
            {
                "description": "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
                "name": "Proxy server",
                "id": 0,
                "key": "PROXY_SERVER",
                "type": "STRING",
            },
            {
                "description": "How often is this collector queried for new data",
                "name": "Refresh interval in minutes",
                "id": 0,
                "key": "REFRESH_INTERVAL",
                "type": "NUMBER",
            },
        ],
        "type": "MANUAL_COLLECTOR",
    },
]