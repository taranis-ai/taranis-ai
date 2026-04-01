# Taranis AI Deployment

Kubernetes deployment configuration with three entrypoints:

- [`kubernetes/`](./kubernetes) for raw manifests plus Kustomize
- [`helm/`](./helm) for the Helm chart
- [`argocd/`](./argocd) for an example ArgoCD `Application` using the Helm chart

Everything is derived from the environment-specific manifests in this repository, with placeholders instead of environment values, upstream `ghcr.io/taranis-ai/*` images, and k3s-oriented defaults.

## Structure

- `kubernetes/`: raw manifests plus `kustomization.yaml`
- `kubernetes/00-config.yaml`: non-secret application settings
- `kubernetes/01-secrets.yaml`: placeholder secrets that must be replaced
- `kubernetes/05-network-policies.yaml`: k3s-oriented network policies
- `kubernetes/10-storage.yaml`: `core` PVC with `local-path` default
- `kubernetes/20-services.yaml`: internal Services
- `kubernetes/30-deployments.yaml`: app Deployments using upstream images with `imagePullPolicy: Always` and explicit `restartPolicy: Always`
- `kubernetes/40-ingress.yaml`: public Ingress placeholder
- `helm/`: Helm chart for the same resource set
- `helm/Chart.yaml`: chart metadata
- `helm/values.yaml`: default placeholders and tunables
- `helm/templates/`: chart templates
- `argocd/`: ArgoCD example files for Helm-based deployment
- `argocd/application.yaml`: example ArgoCD `Application`
- `argocd/values-example.yaml`: example Helm overrides consumed by ArgoCD

## What You Must Configure

Replace every `CHANGE_ME_...` value before deployment.

Required values:

- In `kubernetes/00-config.yaml` or `helm/values.yaml`, set `GRANIAN_HOST`, `TARANIS_BASE_PATH`, and `SSE_PATH`. `TARANIS_AUTHENTICATOR` defaults to `database` and should usually stay unchanged.
- In `kubernetes/01-secrets.yaml` or `helm/values.yaml`, set `JWT_SECRET_KEY`, `API_KEY`, `BOT_API_KEY`, `PRE_SEED_PASSWORD_ADMIN`, `PRE_SEED_PASSWORD_USER`, `DB_URL`, `DB_DATABASE`, `DB_USER`, `DB_PASSWORD`, `QUEUE_BROKER_HOST`, `QUEUE_BROKER_USER`, and `QUEUE_BROKER_PASSWORD`.
- In `kubernetes/10-storage.yaml` or `helm/values.yaml`, override storage settings only if `local-path`, `ReadWriteOnce`, or `1Gi` are not appropriate for your cluster.
- In `kubernetes/40-ingress.yaml` or `helm/values.yaml`, set the public ingress hostname.

## Images

The deployments reference these upstream image paths:

- `ghcr.io/taranis-ai/taranis-core`
- `ghcr.io/taranis-ai/taranis-frontend`
- `ghcr.io/taranis-ai/sse-broker`
- `ghcr.io/taranis-ai/taranis-ingress`
- `ghcr.io/taranis-ai/taranis-worker`
- `ghcr.io/taranis-ai/taranis-natural-language-processing`
- `ghcr.io/taranis-ai/taranis-summarize-bot`
- `ghcr.io/taranis-ai/taranis-story-clustering`

Pin explicit tags before production rollout instead of relying on `latest`.

## Raw Kubernetes

```bash
kubectl apply -k deploy/kubernetes
```

Use [`kubernetes/`](./kubernetes) if you want plain manifests with no Helm dependency.

## Helm

Use [`helm/`](./helm) if you want value-driven rendering or upgrades. The chart keeps `global.imagePullPolicy: Always` and renders pod `restartPolicy: Always` explicitly for all Deployments.

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

After deploying with any of the three approaches, verify:

```bash
kubectl get configmap,secret,pvc,svc,deploy,ingress
kubectl rollout status deploy/core
kubectl rollout status deploy/frontend
kubectl rollout status deploy/sse-broker
kubectl rollout status deploy/ingress
kubectl rollout status deploy/worker
kubectl rollout status deploy/collector
kubectl rollout status deploy/nlp-bot
kubectl rollout status deploy/summary-bot
kubectl rollout status deploy/story-bot
```

Useful checks:

```bash
kubectl logs deploy/core --tail=200
kubectl logs deploy/worker --tail=200
kubectl logs deploy/collector --tail=200
kubectl get endpoints core frontend sse ingress nlp-bot summary-bot story-bot
```

## Notes

- These manifests expect a reachable PostgreSQL service and a reachable RabbitMQ service, but they do not create those workloads.
- The `core` PVC is included because the application writes persistent data under `/app/data`.
- The `core` readiness and liveness probes run every 15 minutes after a 15-second startup delay.
- The default ingress policy assumes the stock k3s Traefik deployment runs in `kube-system` with label `app.kubernetes.io/name=traefik`. Adjust [`05-network-policies.yaml`](./kubernetes/05-network-policies.yaml) or the Helm values if your ingress controller differs.
- The default ingress manifest is plain HTTP. For raw Kubernetes, add `spec.tls` and a certificate secret. For Helm, configure `ingress.tls` and `ingress.annotations` in values.yaml.
