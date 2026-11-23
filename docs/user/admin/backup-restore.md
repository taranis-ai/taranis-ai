---
title: "Backup / Restore"
description: Back up and restore Docker Compose and Kubernetes deployments.
weight: 11
---

Back up PostgreSQL, Core files (`/app/data`), and deployment configuration/secrets together. Redis queues and caches are transient; [Story exports](../assess/story-transfers.md) are not database backups.

## Before you start

Quiesce writers and drain jobs before taking a backup; restore with the matching application release. For encryption, offline copies, and recovery testing, see [CISA's backup guidance](https://www.cisa.gov/stopransomware/ransomware-guide).

## Docker Compose

Use the scripts in [`docker/database/`](https://github.com/taranis-ai/taranis-ai/tree/master/docker/database) from your deployment's `docker/` directory, with its `.env` and Compose project settings.

### Backup

Keep `core` and `database` running; the script executes inside both containers.

```bash
cd /path/to/taranis-ai/docker
umask 077
docker compose stop ingress frontend cron collector workers
bash database/backup.sh
docker compose up -d --wait
```

The script creates `backups/<timestamp>/` containing:

| File | Contents |
| --- | --- |
| `database_backup.tar` | PostgreSQL logical dump (`pg_dump --format=tar`). |
| `core_data.tar.gz` | Core's `/app/data` files. |

Save `.env`, Compose overrides, and image versions separately. Do not run concurrent backups: the scripts use fixed temporary filenames.

### Restore

Restore into a fresh Compose project, setting an unused `COMPOSE_PROJECT_NAME` in its `.env` and retaining the backed-up credentials and application image versions. The script requires absent `<project>_core_data` and `<project>_database_data` volumes; retain the original volumes for rollback.

```bash
cd /path/to/recovery/taranis-ai/docker
docker compose pull
bash database/restore.sh "/secure/backups/<timestamp>"
docker compose up -d --wait
```

Use `--database` or `--core` before the backup directory to restore only that component. Custom volume names and bind mounts require a manual restore.

The current restore script initializes **PostgreSQL 18 Alpine**, mounted at `/var/lib/postgresql`; the recovery Compose configuration must match. Physical archives from `upgrade-database.sh` are incompatible with this script—use the [upgrade rollback procedure](https://github.com/taranis-ai/taranis-ai/blob/master/docker/README.md#upgrade-the-bundled-postgresql-database-to-18).

## Kubernetes and Helm

The [deployment manifests](https://github.com/taranis-ai/taranis-ai/tree/master/deploy) use **external PostgreSQL** and a **`core` PVC** mounted at `/app/data`; there is no Kubernetes backup script. Pair your database provider's backup/restore with a Core PVC snapshot, or use the archive procedure below.

### Prepare storage access

Record replica counts, suspend GitOps/autoscaling, and scale `cron` to zero. After draining jobs, scale `ingress`, `frontend`, `collector`, `worker`, and `core` to zero and wait for their pods to terminate.

Mount the `core` PVC in a temporary pod for backup or restore:

```bash
NS=taranis
kubectl -n "$NS" apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: core-data-maintenance
spec:
  restartPolicy: Never
  containers:
    - name: data
      image: docker.io/library/busybox:1.37.0
      command: ["tail", "-f", "/dev/null"]
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: core
YAML
kubectl -n "$NS" wait --for=condition=Ready pod/core-data-maintenance --timeout=300s
```

### Backup

Configure local PostgreSQL clients for the external database using libpq connection settings and protected credentials, with a matching client major version.

```bash
umask 077
BACKUP_DIR="backups/$(date +%FT%H%M%S)"
mkdir -p "$BACKUP_DIR"
pg_dump --format=tar --file="$BACKUP_DIR/database_backup.tar"
kubectl -n "$NS" exec core-data-maintenance -- \
  tar -czf - -C /data . > "$BACKUP_DIR/core_data.tar.gz"
```

Save manifests or Helm values, image versions, and secrets separately.

### Restore

Prepare a recovery namespace with an empty `core` PVC, a fresh external database, and separate empty Redis; keep application replicas at zero. Restore configuration/secrets and required PostgreSQL roles, point `NS` and the database connection settings at recovery, and create the maintenance pod above.

```bash
BACKUP_DIR="/secure/backups/<timestamp>"
# PGDATABASE must name the recovery database.
pg_restore --exit-on-error --dbname="$PGDATABASE" "$BACKUP_DIR/database_backup.tar"
kubectl -n "$NS" exec -i core-data-maintenance -- \
  tar -xzf - -C /data < "$BACKUP_DIR/core_data.tar.gz"
```

Preserve Core file ownership and use compatible PostgreSQL versions; see [`pg_restore`](https://www.postgresql.org/docs/current/app-pgrestore.html) for ownership mapping.

### Resume

```bash
kubectl -n "$NS" delete pod core-data-maintenance --wait=true
```

Restore recorded replicas and check rollout readiness, then resume GitOps/autoscaling. Keep recovery traffic and outbound publishing isolated until verification.

## Verify recovery

Check `/api/health`, representative Stories/reports and stored files, and Scheduler entries; run a controlled collection before enabling publishing. Retain the original database and storage until recovery is accepted.
