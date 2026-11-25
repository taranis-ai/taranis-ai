---
title: "Collectors"
description: "Collectors are used to gather data from various sources."
weight: 5
---

### Supported options

1. [RSS Collector](https://github.com/taranis-ai/taranis-ai/blob/master/src/worker/worker/collectors/rss_collector.py)
2. [Simple Web Collector](https://github.com/taranis-ai/taranis-ai/blob/master/src/worker/worker/collectors/simple_web_collector.py)
3. [RT Collector](https://github.com/taranis-ai/taranis-ai/blob/master/src/worker/worker/collectors/rt_collector.py)
4. [MISP Collector](https://github.com/taranis-ai/taranis-ai/blob/master/src/worker/worker/collectors/misp_collector.py)
5. [Mastodon Collector](mastodon-collector.md)

The administration view now allows users to use the Preview feature to see the result of the configuration without the items being processed further for the Assess view.
This feature is available for RSS, Simple Web, RT, and Mastodon collectors.

## RSS Collector

RSS Collector enables Taranis AI to collect data from a user-defined RSS feed (See [RSS feeds details](https://rss.com/blog/how-do-rss-feeds-work/)).

* Required fields:
  * **FEED_URL**
* Optional fields:
  * USER_AGENT
  * PROXY_SERVER
  * USE_GLOBAL_PROXY (ignore anything set in the `PROXY_SERVER` field, use what is currently set as a default in [Settings](../settings.md); learn more in section [Settings](../settings.md#default-collector-proxy))
  * ADDITIONAL_HEADERS [accepts a valid `json`] (can be used to add additional headers, not all headers work as expected)
  * CONTENT_LOCATION (selects which field from the RSS entry should be used as the item content, for example `description` or `content:encoded`; when the collector uses content from the RSS entry, it first checks the field named here; if that field is empty or missing, it falls back through `content`, `content:encoded`, `summary`, and `description`)
  * USE_FEED_CONTENT (controls whether the collector uses content from the RSS entry itself or fetches the linked article page; if this is enabled, the collector uses RSS entry content; if it is disabled, the collector fetches the linked article page; if it is not set, a non-empty `CONTENT_LOCATION` effectively enables using RSS entry content)
  * XPATH (optional XPath expression used to limit the extracted content to a specific element; if `USE_FEED_CONTENT` is enabled, XPath is applied to the HTML content taken from the RSS entry; if the XPath does not match, the collector keeps the original RSS entry content; if `USE_FEED_CONTENT` is disabled, XPath is applied to the fetched article page; if the XPath does not match there, the collector does not fall back to another extraction method and the content may be empty)
  * TLP_LEVEL
  * REFRESH_INTERVAL (see [Bots - refresh_interval](../bots.md))
  * DIGEST_SPLITTING On/Off (creates News Items out of URLs present in the `Summary` field of RSS feed)
  * DIGEST_SPLITTING_LIMIT (default: 30)
  * BROWSER_MODE On/Off (see [Browser Mode](#browser-mode))

### Basic configuration

* Example:
  * **FEED_URL**: <https://www.bmi.gv.at/rss/bmi_presse.xml>

### Advanced configuration

The RSS Collector supports the use of XPath for locating elements. (See Simple Web Collector [Advanced configuration](#advanced-configuration-1))

* Example:
  * **FEED_URL**: <https://www.bmi.gv.at/rss/bmi_presse.xml>
  * **XPATH**: //*[@id="getting-started-web-console-creating-new-project_openshift-web-console"]
  * **ADDITIONAL_HEADERS**: `{
    "AUTHORIZATION": "Bearer Token1234",
    "X-API-KEY": "12345",
    "Cookie": "firstcookie=1234; second-cookie=4321",
}`

## Simple Web Collector

Simple Web Collector enables Taranis AI to collect data using web URLs and XPaths.

* Required field:
  * **WEB_URL**
* Optional fields:
  * USER_AGENT
  * PROXY_SERVER
  * USE_GLOBAL_PROXY
  * ADDITIONAL_HEADERS
  * XPATH (set to specify the location of the scraped element on the website)
  * TLP_LEVEL
  * DIGEST_SPLITTING On/Off
  * DIGEST_SPLITTING_LIMIT (default: 30)
  * BROWSER_MODE On/Off (see [Browser Mode](#browser-mode))

### Basic configuration

The simplest way to use this collector is to use the **WEB_URL** field only.
By using only the WEB_URL field, Taranis-AI autonomously determines the content to be collected. Even though it is mostly reliable,
sometimes it is not perfect.

### Advanced configuration

When content cannot be reliably collected using the [Basic configuration](#basic-configuration), adding the attribute **XPATH**
(See [tutorial how to find it](https://www.appsierra.com/blog/how-to-get-xpath-in-chrome)), can be useful.
It is crucial to specify the XPath of the precise element containing the desired data.

### RSS alternative for Mastodon feeds

The native [Mastodon Collector](mastodon-collector.md) is the preferred option because it supports authenticated timelines, account lookup, pagination, and collection cursors. The RSS Collector remains available as a simpler alternative for public hashtag or account feeds exposed by an instance.

To collect a Mastodon RSS feed, follow these steps:

1. **Finding the Mastodon RSS Feed URL**:
   * **Hashtag Feed**: Add `.rss` to the hashtag URL. For example, to collect posts tagged with #cybersecurity:
     ` https://mastodon.social/tags/cybersecurity.rss `
   * **User Feed**: Similarly, add `.rss` to the user's profile URL. Example:
     ` https://mastodon.social/@username.rss `

2. **Creating a New RSS Source with Required Parameters**:
When creating the new RSS source, configure it with the following parameters. Here’s an example of how to fill out the fields:
     * **FEED_URL**: Enter the RSS feed URL for the Mastodon hashtag or user (e.g., `https://mastodon.social/tags/cybersecurity.rss`).
     * **CONTENT_LOCATION**  Set this to `"summary"` to specify the main content location within each RSS entry.
     * **REFRESH_INTERVAL**  Set the refresh interval in crontab-like style, see [Bots - refresh_interval](../bots.md).
     * **DIGEST_SPLITTING** is set to `"false"` since we’re not splitting entries into multiple items.

### Configuration for Darkweb Feeds

Extend your compose.yml with a tor service, e.g.

```yaml
tor:
  image: "docker.io/dperson/torproxy:latest"
  deploy:
    restart_policy:
      condition: always
  environment:
    # LOCATION: "AT"
  logging:
    driver: "json-file"
    options:
      max-size: "200k"
      max-file: "10"
```

Read details about the used docker image [here](https://github.com/dperson/torproxy)

The important setting is "PROXY_SERVER" in the OSINT Source you want to crawl.

## RT Collector

RT Collector enables Taranis AI to collect data from a user-defined [Request Tracker](https://bestpractical.com/request-tracker) instance.

RT Collector collects tickets, translates all ticket attachments into individual News Items. A ticket is represented via a Story. It also collects ticket Custom Fields and saves it as key-value pairs represented with Story attributes, visible whilst Story editing. On each collector execution an update to existing Stories occurs, so editing the Story values in Taranis AI is not recommended and handling it more like read-only items is better.

* Required fields:
  * **BASE_URL**: Base URL of the RT instance (e.g. ```http://localhost```).
  * **RT_TOKEN**: User token for the RT instance.

* Optional fields:
  * SEARCH_QUERY: query to use for filtering tickets (e.g. owner='user1'). It is possible to check this manually by: http://<rt_address>/REST/2.0/tickets?query=owner='user1'
  * FIELDS_TO_INCLUDE: case-sensitive, comma-separated values; example: Email, IP; if not set, all ticket custom fields are ingested
  * ADDITIONAL_HEADERS
  * TLP_LEVEL
  * USER_AGENT
  * PROXY_SERVER
  * USE_GLOBAL_PROXY

## MISP Collector

> Until the [definitions of our MISP Objects](https://github.com/taranis-ai/taranis-ai/tree/master/src/worker/worker/connectors/definitions/objects) are not officially part of the MISP platform, feel free to import them manually (see [MISP Objects](https://www.misp-project.org/2021/03/17/MISP-Objects-101.html/)). This allows to edit the information of News Items and Story data directly in the MISP instance without Taranis AI.

MISP Collector enables Taranis AI to collect [MISP](https://www.misp-project.org/) events.

* Required fields:
  * **URL**: Base URL to the MISP instance (e.g. ```https://localhost```)
  * **API_KEY**: API key to access the instance (see [MISP Automation API](https://www.circl.lu/doc/misp/automation/#automation-api))

* Optional fields:
  * SSL_CHECK: if enabled, the SSL certificate will be validated
  * SHARING_GROUP_ID: set to the ID of a sharing group, if only one sharing group should be collected (see [Create and manage Sharing Groups](https://www.circl.lu/doc/misp/using-the-system/#create-and-manage-sharing-groups)).
  * REQUEST_TIMEOUT
  * USER_AGENT
  * PROXY_SERVER
  * USE_GLOBAL_PROXY
  * ADDITIONAL_HEADERS
  * REFRESH_INTERVAL

### How MISP Collector works

Essentially it works exactly like other collectors with one exception: conflicts. Given the nature of the collaborative environment of MISP events (they can be changed in the MISP platform by the owning organisation and secondary organisations can submit change requests using the [MISP proposals](https://www.circl.lu/doc/misp/using-the-system/#propose-a-change-to-an-event-that-belongs-to-another-organisation)). Due to that, there will likely occur conflicts when attempting to update existing Stories that were, in the meantime, internally modified.

Generally, conflicts occur the moment, a Story is modified internally, and has not been pushed to MISP immediately. Therefore, it is recommended to always try to keep Stories in sync with the MISP events. To update them in MISP with the Story (see [Connectors](../connectors.md)).

## Digest Splitting

Digest Splitting is a feature that allows the user to split all available URLs in the located element into individual News Items.
The Digest Splitting Limit is the maximum number of URLs that will be split into individual News Items. If the limit is reached, the remaining URLs are dropped.
The Digest Splitting Limit is set to 30 News Items by default but can be adjusted by the administrator. Useful in case of timeouts during collection of too many News Items.

## Browser Mode

Collectors will fail if the web page content is only available with JavaScript. In that case it is possible to turn on the **Browser Mode**. All requests will have JavaScript enabled, therefore, it is slower and can use more resources.
