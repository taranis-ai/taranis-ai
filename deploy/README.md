# Taranis AI Deployment

Deployment options:

- [`kubernetes/`](./kubernetes): application services and private LLM inference
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

## Shared LLM endpoint upgrade

Deploy matching Core, frontend, and worker images. Inference needs an amd64 or arm64 node with capacity for its 6 GiB memory request and 12 GiB limit; model loading can take several minutes. See [bundled inference](../docker/README.md#bundled-llm-inference).

Set `LLM_INFERENCE_API_KEY` in `taranis-secrets` (Helm: `secrets.llmInferenceApiKey`) before restarting Core and inference. Both use the same secret; blank disables authentication and clears the stored internal key on restart. Keep credentials out of ConfigMaps.

In **Admin Settings > LLM Endpoints**, verify the default, feature assignments, and bot selections before running jobs. Core registers internal inference on startup without replacing existing selections. Existing Chat configuration becomes a Chat-only endpoint. Workers must be able to reach the selected providers; background story content is sent there. Move custom provider configuration into these settings.

For bots that used `REQUESTS_TIMEOUT` to extend the RQ job deadline, configure `EXECUTION_TIMEOUT` with the required job budget before running them. `REQUESTS_TIMEOUT` now controls only network requests; blank execution timeout uses `RQ_DEFAULT_JOB_TIMEOUT`. Pipelines combine the bot budgets with 20% headroom. Let existing runs finish before upgrading Core and workers together: collection dispatch and staged results now require explicit processed story IDs. Rerun interrupted jobs after the upgrade, and keep the previous parameter values for rollback.

After applying the raw manifests, remove the retired bot Deployments and Services; `kubectl apply -k` does not prune them. Helm removes workloads no longer in the chart. Verify inference, Core, workers, and a representative job for each configured LLM feature.

Keep a database backup and previous images/configuration for rollback: startup removes obsolete bot connection parameters. Restore previous services and settings if reverting, without overwriting newer content. No database schema migration is required.

## Initial settings

Before the first startup, set `PRE_SEED_SETTINGS` in `kubernetes/00-config.yaml`, or `config.preSeedSettings` in Helm values. Both default to `"{}"`. For example:

```yaml
config:
  preSeedSettings: '{"onboarding_enabled":false}'
```

This initializes a fresh settings row only; restarts and upgrades preserve saved Admin Settings. Keep credentials out of these ConfigMaps and inject credential-bearing seeds into core through a Secret instead. See [settings preseeding](../docker/README.md#settings-preseeding).

## Redis without persistence

Kubernetes, Helm, and ArgoCD use an external Redis service. Their manifests cannot
change that server's persistence settings. Configure the external service before
upgrading, including any separate frontend cache instance:

```conf
save ""
appendonly no
```

For a managed service, disable both snapshot and append-only persistence through
its provider settings. For a Redis container, pass `--save "" --appendonly no`
and mount a fresh RAM-backed `/data` (`emptyDir.medium: Memory` in Kubernetes);
do not mount a Redis PVC. Disabling snapshot creation alone does not prevent Redis
from loading an existing `dump.rdb` at startup. Keep the configuration in the
service's deployment source; a live `CONFIG SET` alone will not survive recreation.

Using an authenticated Redis administration connection, verify `CONFIG GET save
appendonly` reports an empty `save` value and `appendonly` set to `no`. Keep the
existing Redis credentials and private network access.

Deploy matching published Core and worker images, then use the rollout checks
below and verify the Scheduler shows the source, bot, and housekeeping schedules.
Cron asks Core to rebuild them from PostgreSQL after an empty Redis restart and
retries through Redis/Core outages. It resumes at the next scheduled run rather
than replaying missed runs. Endpoint checks and empty word-list downloads refresh;
frontend caches refill on demand. Application data, completed task results, and
token revocations remain in PostgreSQL.

Pending one-off jobs, delayed MISP pushes, retries, and unfinished bot chains are
lost on Redis restart. Let important work finish before changing the external
Redis deployment and rerun interrupted actions afterward. Keep the previous
server configuration and application image tags for rollback; older images
require a Core restart after Redis loses state. Avoid reattaching stale queue
files that could replay old publishing jobs. No PostgreSQL migration is required.

## Images

Core uses `ghcr.io/taranis-ai/taranis-core`, `taranis-frontend`, `taranis-ingress`, and `taranis-worker` (for `collector`, `worker`, and `cron`). Realtime uses the pinned `centrifugo/centrifugo:v6.9` image.
Inference uses `ghcr.io/taranis-ai/gemma4-e4b-gguf:cpu`.
Pin explicit tags for production.

Before upgrading, ensure browser access uses HTTPS and the ingress redirects HTTP to HTTPS. With `DEBUG=false` on core and frontend, JWT/CSRF and session cookies are now Secure and HSTS is enabled for one year on the serving hostname. `JWT_COOKIE_SECURE=false` no longer opts out. Keep DEBUG aligned across both services and reserve `DEBUG=true` for isolated development. HSTS omits includeSubDomains/preload, but still affects every application on the same hostname. Rollback to older images does not clear a browser's stored HSTS policy; keep HTTPS available.

Deploy matching Core and frontend versions for story editability: Core supplies the user-specific `can_edit` field, and the frontend defaults missing values to read-only. No database migration is needed for this field. Verify a writable story and an RT-managed or ACL read-only story after upgrading; roll back both components together if needed.

Published `core`, `frontend`, `worker`, and `ingress` images include platform-specific BuildKit SPDX SBOM attestations. The final multi-architecture `core`, `frontend`, and `worker` image digests also have signed CycloneDX attestations generated from their production `uv` lock graphs.
GitHub releases attach the same CycloneDX JSON files for direct download: `taranis_core_sbom.json`, `taranis_frontend_sbom.json`, and `taranis_worker_sbom.json`. See [Software Bills of Materials](../docs/sbom.md) for their scope.

## Raw Kubernetes

```bash
kubectl apply -k deploy/kubernetes
```

## Helm

Use [`helm/`](./helm) for value-driven upgrades. Configure inference with `images.llmInference`, `resources.llmInference`, and `replicas.llmInference`.

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

Set `CHAT_ENABLED=true` on Core and frontend, then select a provider in **Admin Settings > LLM Endpoints**. The Chat section controls the story limit (default 5, range 1–20). Providers must support Responses or Chat Completions with function calling. Chat requires Redis and `ASSESS_ACCESS`; realtime progress is optional.

For custom or outer reverse proxies, allow at least 660 seconds between Chat response reads. Realtime updates use a separate connection and cannot keep the message POST alive.

The provider receives analyst prompts, recent conversation context, and selected story titles, dates, and summaries subject to the analyst's ACL/TLP access. Responses requests use `store: false`; Chat Completions omits `store`. Provider implementations and abuse-monitoring policies may apply their own retention. Select and contract with the provider accordingly, and configure transport security and provider-side retention controls before enabling Chat. Conversations persist until their owner deletes them; disabling Chat preserves that history.

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

Verify inference:

```bash
kubectl rollout status deploy/llm-inference
kubectl get endpoints llm-inference
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
- If moving an externally managed PostgreSQL service to version 18, stop Taranis writers, back up the database, follow its provider's major-version upgrade procedure, and verify the service before restarting Taranis. The Compose upgrade script applies only to the bundled Compose database.
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
