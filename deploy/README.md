# Taranis AI Deployment

Deployment options:

- [`kubernetes/`](./kubernetes): raw Kubernetes core stack
- [`kubernetes-optional-bots/`](./kubernetes-optional-bots): raw Kubernetes overlay that adds `llm-bot`
- [`helm/`](./helm): Helm chart
- [`argocd/`](./argocd): ArgoCD example using the Helm chart

## What You Must Configure

Replace every `CHANGE_ME_...` value before deployment.

Always required:

- In `kubernetes/00-config.yaml` (or `helm/values.yaml`), set `GRANIAN_HOST`.
- In `kubernetes/01-secrets.yaml` (or `helm/values.yaml`), set `JWT_SECRET_KEY`, `API_KEY`, `CENTRIFUGO_API_KEY`, `CENTRIFUGO_CONNECT_PROXY_SECRET`, `PRE_SEED_PASSWORD_ADMIN`, `PRE_SEED_PASSWORD_USER`, `DB_URL`, `DB_DATABASE`, `DB_USER`, `DB_PASSWORD`, `REDIS_URL`, `CENTRIFUGO_REDIS_URL`, and `REDIS_PASSWORD`. Keep the two Centrifugo secrets distinct from each other and from existing application keys.
- The raw manifest provides `TARANIS_BASE_PATH: /`; set it only when serving the application below a subpath.
- When multiple deployments share a domain, set a unique `JWT_COOKIE_SUFFIX` such as `_q` for each deployment and keep it aligned between core and frontend. Helm exposes the same setting as `config.jwtCookieSuffix`.
- The raw manifest keeps the public realtime endpoint at `/sse`; ingress rewrites it to Centrifugo's `/connection/uni_sse`.

Optional `llm-bot` overlay:

- In `kubernetes/00-config.yaml`, set `LLM_BASE_URL`; optionally set `LLM_TIMEOUT` and `LLM_MODEL`.
- In `kubernetes/01-secrets.yaml`, set `BOT_API_KEY`; optionally set `LLM_API_KEY` for providers that require one.
- For Helm, set `config.llmBaseUrl`; optionally set `config.llmTimeout`, `config.llmModel`, and `secrets.llmApiKey`.
- Set ingress hostname in `kubernetes/40-ingress.yaml` (or Helm values).

Optional analyst Chat:
- Set `CHAT_ENABLED=true` in configuration for both core and frontend.
- Open **Admin Settings > Chat** to configure the provider base URL, model, API key, provider timeout (default 120 seconds), and maximum stories (default 5, allowed 1-20). This collapsible section appears only when Chat is enabled. Values are persisted in Settings; changes apply to the next message without restarting. Only `CHAT_ENABLED` is configured through deployment environment variables.
- API keys are write-only in the admin form: leave blank to keep the saved key, or select **Remove saved API key** to clear it. Keys are stored in the application database; protect database access and backups. Settings API responses and logs omit the key.
- Realtime Chat progress uses the existing Centrifugo connection when `REALTIME_ENABLED=true`; Chat still completes through its normal HTTP response when realtime is disabled or unavailable.

## Initial settings

Before the first startup, set `PRE_SEED_SETTINGS` in `kubernetes/00-config.yaml`, or the JSON string `config.preSeedSettings` in Helm values. Both default to `"{}"`. For example, Helm values can contain:

```yaml
config:
  preSeedSettings: '{"onboarding_enabled":false}'
```

This initializes a fresh settings row only; restarts and upgrades preserve saved Admin Settings. Keep credentials out of these ConfigMaps and inject credential-bearing seeds into core through a Secret instead. See [settings preseeding](../docker/README.md#settings-preseeding).

## Images

Core uses `ghcr.io/taranis-ai/taranis-core`, `taranis-frontend`, `taranis-ingress`, and `taranis-worker` (for `collector`, `worker`, and `cron`). Realtime uses the pinned `centrifugo/centrifugo:v6.9` image.
Optional overlay uses `ghcr.io/taranis-ai/taranis-llm-bot:latest`.
Pin explicit tags for production.

Published `core`, `frontend`, `worker`, and `ingress` images include platform-specific BuildKit SPDX SBOM attestations. The final multi-architecture `core`, `frontend`, and `worker` image digests also have signed CycloneDX attestations generated from their production `uv` lock graphs.
GitHub releases attach the same CycloneDX JSON files for direct download: `taranis_core_sbom.json`, `taranis_frontend_sbom.json`, and `taranis_worker_sbom.json`. See [Software Bills of Materials](../docs/sbom.md) for their scope.

## Raw Kubernetes

```bash
kubectl apply -k deploy/kubernetes
```

```bash
kubectl apply -k deploy/kubernetes-optional-bots
```

`kubernetes` is core-only. `kubernetes-optional-bots` includes core plus `llm-bot`.
Default bot endpoints target `llm-bot` routes: `/summarize`, `/title`, `/ner`, `/cluster`, `/sentiment`, and `/cybersec-classification`.

## Helm

Use [`helm/`](./helm) if you want value-driven rendering or upgrades. The chart keeps `global.imagePullPolicy: Always` and renders pod `restartPolicy: Always` explicitly for all Deployments.
Helm deploys one `llm-bot` workload for summarization, title generation, NER, story clustering, sentiment analysis, and cybersecurity classification.

```bash
helm template taranis deploy/helm
helm upgrade --install taranis deploy/helm
```

## ArgoCD

Use [`argocd/`](./argocd) if you want GitOps deployment through the Helm chart.

1. Edit `argocd/application.yaml`:
   `spec.project`, `spec.source.repoURL`, `spec.source.targetRevision`, `spec.destination.namespace`
1. Edit `argocd/values-example.yaml` with your ingress hostname, storage overrides, database values, Redis values, secrets, and image tags.
1. Apply the application:

```bash
kubectl apply -f deploy/argocd/application.yaml
```

## Analyst Chat

Chat is independent of `llm-bot` and workers. Core calls the configured OpenAI-compatible Responses API directly and uses Redis only for a bounded per-conversation turn lease. If Redis is unavailable, new turns return 503 rather than risk out-of-order conversation history. Analysts need `ASSESS_ACCESS`; all generated Assess searches continue to enforce their source ACLs and TLP restrictions.

Core first makes a structured routing call, then requests a streaming plain-text answer. Providers that reject Responses streaming before sending any content fall back to the structured non-streaming answer contract. When realtime is enabled, Core publishes progress stage identifiers and cumulative answer snapshots to the authenticated user's existing Centrifugo channel; the frontend localizes the stages. These publications are best-effort and have no history; the final synchronous response and PostgreSQL conversation remain authoritative.

Chat turns share a 540-second deadline across provider planning, retries, search, and answering, checked again before persistence. Provider reads retain the configured per-read timeout; the total deadline stops active response reads even when bytes keep arriving. The Redis lease lasts 570 seconds, reserving 30 seconds for transaction cleanup and release. The frontend HTTP timeout remains 600 seconds.

Enabling Chat creates `chat_conversation` and `chat_message` tables at core startup. Conversations and answers remain in Taranis until their owner deletes them. The provider receives the analyst's prompt, up to the latest 10 saved chat messages, the analyst-visible filter catalog, and, for search answers, up to the configured `chat_max_stories` bounded story summaries. Raw news-item content and provider credentials are not saved in chat metadata.

This is a data-egress boundary: analyst prompts and selected story titles, dates, and summaries leave Taranis for the configured provider. Core requests `store: false`, but provider implementations and abuse-monitoring policies may apply their own retention. Select and contract with the provider accordingly, and configure transport security and provider-side retention controls before enabling the feature.

Rollback is non-destructive. Set `CHAT_ENABLED=false` on core and frontend and restart the published application images; navigation disappears and core returns 503 for Chat calls, while the tables and conversation history remain untouched. Older images ignore the new tables.

## Validation

Verify base services:

```bash
kubectl get configmap,secret,pvc,svc,deploy,ingress
kubectl rollout status deploy/core
kubectl rollout status deploy/frontend
kubectl rollout status deploy/centrifugo
kubectl rollout status deploy/ingress
kubectl rollout status deploy/worker
kubectl rollout status deploy/collector
kubectl rollout status deploy/cron
```

If optional overlay is enabled:

```bash
kubectl rollout status deploy/llm-bot
kubectl get endpoints llm-bot
```

Useful logs:

```bash
kubectl logs deploy/core --tail=200
kubectl logs deploy/worker --tail=200
kubectl logs deploy/collector --tail=200
kubectl logs deploy/cron --tail=200
```

## Collector network errors

For HTTP connection failures or timeouts in collectors using the shared HTTP request helper (including RSS, Simple Web, and RT), check DNS resolution and outbound access from the worker/collector container or pod; successful resolution on the host alone is insufficient. A read timeout can also occur after a connection succeeds. If a proxy is required, verify the source's `PROXY_SERVER` URL and that its hostname resolves inside the container. A proxy IP can help diagnose a hostname-resolution problem, but should not replace fixing DNS. Check worker/collector logs for the underlying error, then run the collection again. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. No automatic retry policy is added by these diagnostic messages.

## Operational CLI

Run `taranis-cli` inside the core container for emergency user administration.

```bash
kubectl exec -it deploy/core -- taranis-cli set-password admin
kubectl exec -it deploy/core -- taranis-cli set-roles user Admin
```

For Docker Compose-style deployments:

```bash
docker exec -it core taranis-cli set-password admin
docker exec -it core taranis-cli set-roles user Admin
```

`set-password` updates an existing user's database-auth password. `set-roles` replaces an existing user's full role list; role arguments are exact role names or role IDs. Prefer the password prompt or `--password-stdin` instead of passing passwords as command arguments.

## Notes

- These manifests expect a reachable PostgreSQL service and a reachable Redis service, but they do not create those workloads.
- `STORY_API_ENDPOINT` now defaults to `http://llm-bot:8000/cluster`; ensure your `llm-bot` image exposes that route if you enable story clustering.
- The `core` PVC is included because the application writes persistent data under `/app/data`.
- The `core` readiness and liveness probes run every 5 minutes after a 15-second startup delay because the core healthcheck performs non-trivial service checks.
- The default `core` and `frontend` images recycle Granian workers above 4096 MiB and 1024 MiB RSS respectively.
- The default ingress policy assumes the stock k3s Traefik deployment runs in `kube-system` with label `app.kubernetes.io/name=traefik`. Adjust [`05-network-policies.yaml`](./kubernetes/05-network-policies.yaml) or the Helm values if your ingress controller differs.
- The default ingress manifest is plain HTTP. For raw Kubernetes, add `spec.tls` and a certificate secret. For Helm, configure `ingress.tls` and `ingress.annotations` in values.yaml.

## Frontend smoke check

After updating the frontend image, check table search, sorting, page size, and pagination with JavaScript enabled and disabled. With JavaScript enabled, verify that search focus survives updates and failed requests display notifications without replacing the table.

For dashboard updates, deploy matching core and frontend images so weekly activity fields are available. Check the four workflow cards, weekly counts, and permission-gated analyst review link. Verify that users without review permission have no empty header action area. No database migration is required.

## SFTP publisher host trust

Configure host trust in **Admin → Publisher Presets → SFTP Publisher → Optional settings**.
Upload the server's `.pub` file or paste its OpenSSH public key (`key-type base64-key`,
with an optional comment) into **Server host public key**. Verify its fingerprint with
the server administrator through a trusted channel. The key applies to the destination
in the SFTP URL, including non-default ports. Changed server keys fail publishing.
The public key is stored in the preset's `HOST_KEY` parameter; no image changes,
worker filesystem mounts, or restarts are needed when updating a key.

Alternatively, explicitly enable **Accept any server host key (insecure)**
(`ACCEPT_ANY_HOST_KEY=true`). This ignores any supplied key and disables server identity
verification, allowing man-in-the-middle attacks. It defaults to false. Without a key
or this explicit opt-in, configuration and publishing fail. The client authentication
`PRIVATE_KEY` parameter is separate from the server's public host key.

Deploy matching core, frontend, and worker images for these parameters. For existing
SFTP presets, configure one of the two options before publishing; mounted `known_hosts`
files are no longer used. Pull the selected published images, restart services, verify
health, and publish a test product. No database migration is required. Before rolling
back, export the presets and remove the new parameters for older schema versions;
the prior worker version requires its documented `known_hosts` setup.
