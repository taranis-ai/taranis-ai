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
- In `kubernetes/01-secrets.yaml` (or `helm/values.yaml`), set `JWT_SECRET_KEY`, `API_KEY`, `PRE_SEED_PASSWORD_ADMIN`, `PRE_SEED_PASSWORD_USER`, `DB_URL`, `DB_DATABASE`, `DB_USER`, `DB_PASSWORD`, `REDIS_URL`, `REDIS_PASSWORD`.
- The raw manifest provides `TARANIS_BASE_PATH: /`; set it only when serving the application below a subpath.
- The raw manifest provides `SSE_PATH: /sse`; keep it aligned with the ingress SSE route if you change it.

Optional `llm-bot` overlay:
- In `kubernetes/00-config.yaml`, set `LLM_BASE_URL`; optionally set `LLM_TIMEOUT` and `LLM_MODEL`.
- In `kubernetes/01-secrets.yaml`, set `BOT_API_KEY`; optionally set `LLM_API_KEY` for providers that require one.
- Set ingress hostname in `kubernetes/40-ingress.yaml` (or Helm values).

Optional analyst Chat:
- Set `CHAT_ENABLED=true` in configuration for both core and frontend.
- Set `CHAT_LLM_BASE_URL` to the provider's OpenAI-compatible API base URL. Core sends requests to `{CHAT_LLM_BASE_URL}/responses`.
- Set `CHAT_LLM_MODEL` when required by the provider. `CHAT_LLM_TIMEOUT` defaults to 120 seconds and `CHAT_MAX_STORIES` defaults to 5.
- Store `CHAT_LLM_API_KEY` only in the deployment secret. It may be empty when the provider does not require bearer authentication.
- `CHAT_REQUEST_TIMEOUT` is frontend-only and defaults to 300 seconds to cover the synchronous planner and answer calls.

## Images

Core uses `ghcr.io/taranis-ai/taranis-core`, `taranis-frontend`, `sse-broker`, `taranis-ingress`, and `taranis-worker` (for `collector`, `worker`, and `cron`).
Optional overlay uses `ghcr.io/taranis-ai/taranis-llm-bot:latest`.
Pin explicit tags for production.

Published `core`, `frontend`, `worker`, and `ingress` images include registry SBOM attestations.
GitHub releases attach CycloneDX JSON SBOM files for the Python application environments: `taranis_core_sbom.json`, `taranis_frontend_sbom.json`, and `taranis_worker_sbom.json`.

## Raw Kubernetes

```bash
kubectl apply -k deploy/kubernetes
```

```bash
kubectl apply -k deploy/kubernetes-optional-bots
```

`kubernetes` is core-only. `kubernetes-optional-bots` includes core plus `llm-bot`.
Default bot endpoints target `llm-bot` routes: `/summarize`, `/ner`, `/cluster`.

## Helm

Use [`helm/`](./helm) if you want value-driven rendering or upgrades. The chart keeps `global.imagePullPolicy: Always` and renders pod `restartPolicy: Always` explicitly for all Deployments.
Helm currently still uses legacy `nlp-bot`, `summary-bot`, and `story-bot` workloads.

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

Chat is independent of `llm-bot`, Redis, and workers. Core calls the configured OpenAI-compatible Responses API directly. Analysts need `ASSESS_ACCESS`; all generated Assess searches continue to enforce their source ACLs and TLP restrictions.

Enabling Chat creates `chat_conversation` and `chat_message` tables at core startup. Conversations and answers remain in Taranis until their owner deletes them. The provider receives the analyst's prompt, up to the latest 10 saved chat messages, the analyst-visible filter catalog, and, for search answers, up to `CHAT_MAX_STORIES` bounded story summaries. Raw news-item content and provider credentials are not saved in chat metadata.

This is a data-egress boundary: analyst prompts and selected story titles, dates, and summaries leave Taranis for the configured provider. Core requests `store: false`, but provider implementations and abuse-monitoring policies may apply their own retention. Select and contract with the provider accordingly, and configure transport security and provider-side retention controls before enabling the feature.

Rollback is non-destructive. Set `CHAT_ENABLED=false` on core and frontend and restart the published application images; navigation disappears and core returns 503 for Chat calls, while the tables and conversation history remain untouched. Older images ignore the new tables.

## Validation

Verify base services:

```bash
kubectl get configmap,secret,pvc,svc,deploy,ingress
kubectl rollout status deploy/core
kubectl rollout status deploy/frontend
kubectl rollout status deploy/sse-broker
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
