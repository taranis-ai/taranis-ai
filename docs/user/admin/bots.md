---
title: "Bots"
description: "Bots enrich collected Stories and News Items in the background."
weight: 5
---

Bots run as worker jobs. They can be triggered manually, scheduled with `REFRESH_INTERVAL`, or run after collection when `RUN_AFTER_COLLECTOR` is enabled.

## Available bots

| Bot | Purpose |
| --- | --- |
| Analyst Bot | Adds configured attributes based on regular expression matches. |
| Grouping Bot | Groups News Items by regular expression matches. |
| Tagging Bot | Adds tags based on regular expression matches. |
| Wordlist Bot | Tags News Items with configured word lists. |
| IOC Bot | Detects indicators of compromise in News Items. |
| NLP Bot | Sends text to an NLP endpoint for named entity tags. |
| Story Clustering Bot | Sends Stories to a clustering endpoint and groups related items. |
| Summary Bot | Generates Story summaries and, optionally, Story titles. |
| Sentiment Analysis Bot | Adds sentiment attributes to News Items. |
| Cybersecurity Classifier Bot | Classifies whether Story content is cybersecurity related. |
| IntelOwl Bot | Enriches IOC tags through an IntelOwl instance. |

Implementation details are available in the [worker bot source](https://github.com/taranis-ai/taranis-ai/tree/master/src/worker/worker/bots).

## Common settings

| Setting | Purpose |
| --- | --- |
| Name | Display name in the admin UI. |
| Description | Operator-facing description. |
| Type | Bot implementation to run. |
| Index | Execution order when multiple bots run after collection. |
| `RUN_AFTER_COLLECTOR` | Runs the bot after collector jobs. |
| `RUN_AFTER_BOTS` | Optional configured bot instances that must finish before this bot runs. |
| `REFRESH_INTERVAL` | Cron-like schedule, for example `0 */8 * * *`. |
| `REQUESTS_TIMEOUT` | HTTP timeout for calls to external bot services. |
| `BOT_API_KEY` | API key sent to external bot services when needed. |

Scheduled bots are handled by Redis/RQ. See [Background Jobs](../getting-started/07_background-jobs.md) for worker and scheduler health checks.

Use the bot run-order editor instead of entering `RUN_AFTER_BOTS` manually. Bot dependencies refer to configured bot instances, not bot types. The IntelOwl Bot depends on the IOC Bot so it can enrich extracted indicators.

## LLM-backed bots

The optional [LLM Bot Service](../getting-started/08_llm-bot.md) can serve several bot endpoints.

| Bot | Worker default | Per-bot override | Typical `llm-bot` endpoint |
| --- | --- | --- | --- |
| Summary Bot | `SUMMARY_API_ENDPOINT` | `SUMMARY_ENDPOINT` | `http://llm-bot:8000/summarize` |
| Summary Bot title generation | none | `TITLE_ENDPOINT` | `http://llm-bot:8000/title` |
| NLP Bot | `NLP_API_ENDPOINT` | `BOT_ENDPOINT` | `http://llm-bot:8000/ner` |
| Story Clustering Bot | `STORY_API_ENDPOINT` | `BOT_ENDPOINT` | `http://llm-bot:8000/cluster` |
| Sentiment Analysis Bot | `SENTIMENT_ANALYSIS_API_ENDPOINT` | `BOT_ENDPOINT` | `http://llm-bot:8000/sentiment` |

Per-bot endpoint fields take precedence over worker environment defaults. After upgrading from older standalone bot services, update LLM-backed bot parameters that still point to `summary_bot`, `nlp_bot`, `story_bot`, or `sentiment_analysis_bot`. If you keep the Cybersecurity Classifier Bot, make sure its configured classifier endpoint is still deployed.

The Summary Bot only updates Story titles when `TITLE_ENDPOINT` is configured and the Story contains more than one News Item.

## Sentiment output

The Sentiment Analysis Bot writes these News Item attributes:

- `sentiment_score`
- `sentiment_category`

The Story Edit advanced view displays the sentiment status when these attributes are present.

## IntelOwl enrichment

The [IntelOwl enrichment guide](intelowl.md) covers required analyzers, bot configuration, and viewing CTI results.
