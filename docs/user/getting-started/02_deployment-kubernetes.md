---
title: Kubernetes deployment
description: How to deploy Taranis AI on Kubernetes
weight: 2
---

For database and persistent-volume backups and recovery, see [Backup / Restore](../admin/backup-restore.md#kubernetes-and-helm).

## Configuration

Clone via git

```bash
git clone --depth 1  https://github.com/taranis-ai/taranis-ai
cd taranis-ai/docker/
```

Copy `env.sample` to `.env`

```bash
cp env.sample .env
```

Open file `.env` and change defaults if needed. More details about environment variables can be found [here](https://github.com/taranis-ai/taranis-ai/blob/master/docker/README.md).

See [Internal TLS Configuration](20_tls-configuration.md) for setting up TLS encryption and [Advanced monitoring](15_advanced-monitoring.md) for more logging insights.
See [Releases and Container Tags](05_releases-and-tags.md) for information about container image versions, [Internal TLS Configuration](20_tls-configuration.md) for setting up TLS encryption, and [Advanced monitoring](15_advanced-monitoring.md) for more logging insights.

## Convert via Kompose

Download and install [kompose.io](https://kompose.io/installation/)

```bash
# resovle variables from .env into taranis-ai/docker/compose.yml
docker compose config > resolved-compose.yml

# convert compose file to kubernetes
kompose --file resolved-compose.yaml convert
```

## MultiDB SQLAlchemy

If you want to connect to a kubernetes cluster you can do something like this:

```bash
kubectl create ns db
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install pg-ha bitnami/postgresql-ha -n db \
  --set postgresql.username=app \
  --set postgresql.password=apppass \
  --set postgresql.database=appdb \
  --set pgpool.adminUsername=pgpool \
  --set pgpool.adminPassword=pgpoolpass \
  --set postgresql.replicaCount=2

kubectl -n db port-forward statefulset/pg-ha-postgresql 54321:5432 &
kubectl -n db port-forward pod/pg-ha-postgresql-1 54322:5432 &
```

And then connect with:

```
SQLALCHEMY_DATABASE_URI="postgresql+psycopg://app:apppass@/appdb?host=127.0.0.1,127.0.0.1&port=54321,54322&target_session_attrs=read-write&connect_timeout=3"
```
