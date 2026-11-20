---
title: "LLM Bot Service"
description: Configure the optional LLM-backed bot service for summaries, titles, NER, clustering, and sentiment.
weight: 8
---

`llm-bot` is an optional HTTP service used by worker bots for LLM-backed analysis. The Compose deployment includes it as `ghcr.io/taranis-ai/taranis-llm-bot:${TARANIS_BOT_TAG:-stable}`.

It talks to an OpenAI-compatible Responses API and exposes endpoints for:

| Endpoint | Purpose |
| --- | --- |
| `/summarize` | Generate a story summary. |
| `/title` | Generate a concise story title. |
| `/ner` | Extract named entities. |
| `/cluster` | Cluster related stories. |
| `/sentiment` | Analyze sentiment. |
| `/ner-link` | Extract entities and link them to candidates. |
| `/link` | Link supplied entities to candidates. |
| `/health` | Readiness check. |
| `/info` | Non-secret service capabilities and active config. |

## Compose configuration

Set these values in `docker/.env`:

| Variable | Purpose |
| --- | --- |
| `BOT_API_KEY` | Shared secret used by workers when calling bot services. |
| `LLM_BASE_URL` | Base URL of the upstream OpenAI-compatible API. |
| `LLM_API_KEY` | Upstream API key. |
| `LLM_MODEL` | Model name, unless the upstream provides a default. |
| `LLM_TIMEOUT` | Upstream request timeout in seconds. |
| `LLM_BOT_PORT` | Internal service port, default `8000`. |

Advanced optional settings:

| Variable | Purpose |
| --- | --- |
| `LLM_REASONING_PROFILE` | Prompt handling profile for models that emit reasoning text. Supported values include `none`, `ministral`, and `gemma`. |
| `LLM_REASONING_EFFORT` | Optional upstream reasoning effort value, for example `low`, `medium`, or `high`. |
| `LLM_STRIP_REASONING_OUTPUT` | Strip reasoning blocks before parsing model output. |
| `LLM_PARSE_REASONING_AS_OUTPUT` | Use structured reasoning text as fallback output when the provider emits no final message. |
| `LOOKUP_BASE_URL` | Optional lookup API used by entity linking. |
| `LOOKUP_API_KEY` | API key for the lookup API. |
| `LOOKUP_DEFAULT_LANGUAGE` | Default language for entity lookup. |
| `LOOKUP_CANDIDATE_LIMIT` | Number of lookup candidates considered per entity. |
| `NER_LINKING_ENABLED` | Enables linked NER output paths. |
| `NER_LINKING_MODE` | `deterministic` or `llm`. |
| `SUMMARY_ROUTE_PATH` | Override the summary route path. Default: `/summarize`. |
| `NER_ROUTE_PATH` | Override the NER route path. Default: `/ner`. |

Keep `LLM_API_KEY`, `BOT_API_KEY`, and any provider credentials out of logs and shared files. The service should stay on the private application network; do not publish it directly to the internet.

## Worker integration

The Compose deployment wires these worker endpoints to `llm-bot` by default:

| Worker variable | Default endpoint |
| --- | --- |
| `SUMMARY_API_ENDPOINT` | `http://llm-bot:8000/summarize` |
| `NLP_API_ENDPOINT` | `http://llm-bot:8000/ner` |
| `STORY_API_ENDPOINT` | `http://llm-bot:8000/cluster` |

Bot endpoint parameters saved in the admin UI take precedence over worker defaults. If an upgraded instance still has old standalone bot hostnames such as `http://summary_bot:8000`, `http://nlp_bot:8000`, or `http://story_bot:8000`, update those bot parameters to the `llm-bot` endpoints or clear the override.

For title generation, set `TITLE_ENDPOINT` on the Summary Bot to:

```text
http://llm-bot:8000/title
```

For sentiment analysis, set the Sentiment Analysis Bot `BOT_ENDPOINT` to:

```text
http://llm-bot:8000/sentiment
```

Each bot can override the default endpoint and timeout with its own parameters. See [Bots](../admin/bots.md) for the user-facing bot settings.

Canonical `llm-bot` paths are accepted with or without a trailing slash.

## Validation

Check service health from inside the application network:

```bash
curl http://llm-bot:8000/health
```

If `API_KEY` is configured on the service, protected task endpoints require:

```http
Authorization: Bearer <BOT_API_KEY>
```

Use `/info` to confirm endpoint paths and non-secret feature settings. It reports whether lookup and linking are configured without exposing API keys.
