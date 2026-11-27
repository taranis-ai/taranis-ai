---
title: Chat deployment
description: Enable analyst Chat and verify its provider, Redis, and proxy requirements.
weight: 9
---

[Analyst Chat](../chat/_index.md) is optional and disabled by default. It requires core, frontend, the application database, Redis, and a reachable provider supporting Responses or Chat Completions with function calling. Core calls the provider directly; Chat does not require `llm-bot` or workers.

## Enable Chat

For the standard Compose deployment, set this in `.env`:

```dotenv
CHAT_ENABLED=true
```

The shipped Compose configuration passes this flag to both **core** and **frontend**. Custom deployments must enable it on both services. For Kubernetes, set `CHAT_ENABLED: "true"` in the deployment ConfigMap; for Helm, set `config.chatEnabled: "true"`.

Use published application images containing Chat support. From the Compose deployment directory, pull the configured images and recreate the application services:

```bash
docker compose pull core frontend
docker compose up -d core frontend
docker compose ps
```

Check `/api/health` at your deployment URL and confirm database and Redis health in the [Admin Dashboard](../dashboard/administration.md). Then open **Administration > Settings > Chat** and [configure the provider](../admin/chat.md). Only `CHAT_ENABLED` is a deployment environment setting for Chat; the provider URL, API format, model, key, timeout, and Story limit are saved in Admin Settings.

Analysts need `ASSESS_ACCESS`. Verify a general answer, a Story search and its Assess link, and saved conversation history before making Chat available to analysts. A visible Chat navigation item alone does not confirm that the provider is working.

## Runtime and proxy requirements

Redis coordinates concurrent requests. If it is unavailable, new messages fail with **Chat is temporarily unavailable**. Check Redis connectivity from core when this occurs.

With `REALTIME_ENABLED=true` and live updates connected, analysts receive progress stages and streamed answer text. Realtime is optional: the completed answer still arrives through the normal HTTP response.

A Chat turn has an overall **540-second** deadline. The frontend waits up to **600 seconds** for core. The shipped ingress allows **660 seconds** between upstream reads for Chat requests. Configure custom or outer reverse proxies with a Chat response timeout of at least **660 seconds**, including any application base path. Progress updates use a separate connection and do not keep the message POST alive.

Provider settings apply on the next message, but changing `CHAT_ENABLED` requires restarting or recreating core and frontend. Startup creates the Chat tables. Include conversations and provider settings in your database backup and access-control planning; see [privacy and storage](../admin/chat.md#privacy-and-storage).

## Disable or roll back

Set `CHAT_ENABLED=false` for both core and frontend and recreate those services. This removes Chat from navigation and disables the API while preserving conversations and settings. Re-enabling Chat restores access to saved history.

If rolling back application images, restore the previously deployed image tags and follow the same pull, recreate, and health-check steps. Older images ignore the Chat tables; disabling the feature does not require dropping them.
