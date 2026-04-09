# Taranis AI Deployment

Deployment options:

- [`kubernetes/`](./kubernetes): raw Kubernetes core stack
- [`kubernetes-optional-bots/`](./kubernetes-optional-bots): raw Kubernetes overlay that adds `llm-bot`
- [`helm/`](./helm): Helm chart
- [`argocd/`](./argocd): ArgoCD example using the Helm chart

## What You Must Configure

Replace every `CHANGE_ME_...` value before deployment.

Always required:
- In `kubernetes/00-config.yaml` (or `helm/values.yaml`), set `GRANIAN_HOST`, `TARANIS_BASE_PATH`, `SSE_PATH`.
- In `kubernetes/01-secrets.yaml` (or `helm/values.yaml`), set `JWT_SECRET_KEY`, `API_KEY`, `PRE_SEED_PASSWORD_ADMIN`, `PRE_SEED_PASSWORD_USER`, `DB_URL`, `DB_DATABASE`, `DB_USER`, `DB_PASSWORD`, `QUEUE_BROKER_HOST`, `QUEUE_BROKER_USER`, `QUEUE_BROKER_PASSWORD`.

Optional `llm-bot` overlay:
- In `kubernetes/00-config.yaml`, set `LLM_BASE_URL`, `LLM_MODEL` (and optionally `LLM_TIMEOUT`).
- In `kubernetes/01-secrets.yaml`, set `BOT_API_KEY`, `LLM_API_KEY`.
- Set ingress hostname in `kubernetes/40-ingress.yaml` (or Helm values).

## Images

Core uses `ghcr.io/taranis-ai/taranis-core`, `taranis-frontend`, `sse-broker`, `taranis-ingress`, `taranis-worker`.
Optional overlay uses `ghcr.io/taranis-ai/taranis-llm-bot:latest`.
Pin explicit tags for production.

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
1. Edit `argocd/values-example.yaml` with your ingress hostname, storage overrides, database values, RabbitMQ values, secrets, and image tags.
1. Apply the application:

```bash
kubectl apply -f deploy/argocd/application.yaml
```

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
```

## Notes

- These manifests expect a reachable PostgreSQL service and a reachable RabbitMQ service, but they do not create those workloads.
- `STORY_API_ENDPOINT` now defaults to `http://llm-bot:5500/cluster`; ensure your `llm-bot` image exposes that route if you enable story clustering.
- The `core` PVC is included because the application writes persistent data under `/app/data`.
- The `core` readiness and liveness probes run every 15 minutes after a 15-second startup delay.
- The default ingress policy assumes the stock k3s Traefik deployment runs in `kube-system` with label `app.kubernetes.io/name=traefik`. Adjust [`05-network-policies.yaml`](./kubernetes/05-network-policies.yaml) or the Helm values if your ingress controller differs.
- The default ingress manifest is plain HTTP. For raw Kubernetes, add `spec.tls` and a certificate secret. For Helm, configure `ingress.tls` and `ingress.annotations` in values.yaml.
