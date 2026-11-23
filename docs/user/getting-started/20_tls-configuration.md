---
title: "TLS Configuration"
linkTitle: "TLS Configuration"
weight: 20
description: >
  Configure TLS encryption for Taranis AI using Granian ASGI server with SSL certificates and proper environment variables.
---

This guide explains how to configure TLS (Transport Layer Security) for Taranis AI using the Granian ASGI server. TLS provides encrypted communication between clients and the server, essential for secure deployments.

## Key Environment Variables

The primary TLS configuration is handled through Granian environment variables:

### Required TLS Variables

For a basic TLS setup, configure these environment variables:

```bash
# SSL Certificate file path
GRANIAN_SSL_CERTIFICATE=/path/to/your/certificate.pem

# SSL Private key file path
GRANIAN_SSL_KEYFILE=/path/to/your/private_key.pem

# Turn off verification of self-signed certificates in Frontend and Worker service
SSL_VERIFICATION=False

DISABLE_SSE=True
```

When enabling TLS, you must also update the core URL to use HTTPS:

```bash
# Update the core API URL to use HTTPS
TARANIS_CORE_URL=https://your-domain.com/api
```

This variable affects multiple components:

- **Frontend service**: Uses `TARANIS_CORE_URL` to communicate with the core API
- **Worker service**: Uses `TARANIS_CORE_URL` for API communication (falls back to `http://{TARANIS_CORE_HOST}{TARANIS_BASE_PATH}api` if not set)
- **GUI service**: Configured via `TARANIS_CORE_API` in config.json

### Optional TLS Variables

More [Granian environmental variables](https://github.com/emmett-framework/granian?tab=readme-ov-file#options) that affect SSL are derived from the CLI options prefixed with `--ssl-*`.

Examples:

```bash
GRANIAN_SSL_KEYFILE_PASSWORD
GRANIAN_SSL_CA
GRANIAN_SSL_CRL
GRANIAN_SSL_CLIENT_VERIFY
```

Make sure, all variables are properly set in the [compose file](https://github.com/taranis-ai/taranis-ai/blob/master/docker/compose.yml). The variable `SSL_VERIFICATION` can be set for the `frontend` and `worker` service.

## Docker Compose Configuration

### Important Configuration Notes

1. **Certificate Mounting**: Certificates mounted as read-only (`./certs:/certs:ro`)
2. **SSL Verification**: Self-signed certificates cause problems (`SSL_VERIFICATION=False`)
3. **Health Checks**: To work properly they need to be changed to `https://` prefix. Moreover, the Certificate Authority needs to be added into the container's trust store by mounting it under /usr/local/share/... Read more at [docker.com](https://docs.docker.com/engine/network/ca-certs/).

### Basic TLS Setup

Here's an example Docker Compose configuration with TLS enabled:

```yaml
services:
  core:
    image: ghcr.io/taranis-ai/taranis-core:latest
    environment:
      # TLS configuration (paths must match the mounted cert directory)
      - GRANIAN_SSL_CERTIFICATE=/certs/certificate.pem
      - GRANIAN_SSL_KEYFILE=/certs/private_key.pem

      - TARANIS_CORE_URL=https://your-domain.com/api
      - DB_URL=database
      - DB_DATABASE=taranis
      - DB_USER=taranis
      - DB_PASSWORD=supersecret
      - API_KEY=your-secure-api-key
      - JWT_SECRET_KEY=your-secure-jwt-secret

    volumes:
      # Mount local certificate directory into the container
      - ./certs:/certs:ro
      - core_data:/app/data

    depends_on:
      - database
      - rabbitmq

    ports:
      - "8443:8080"

    networks:
      - taranis_network

    healthcheck:
      test: ["CMD-SHELL", "curl --fail https://localhost:8080/api/health || exit 1"]
      interval: 90s
      timeout: 30s
      retries: 5
      start_period: 40s

volumes:
  core_data:

networks:
  taranis_network:
    driver: bridge
```

## Kubernetes Configuration

For Kubernetes deployments, configure TLS using ConfigMaps and Secrets:

```yaml
# TLS Secret
apiVersion: v1
kind: Secret
metadata:
  name: taranis-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-certificate>
  tls.key: <base64-encoded-private-key>

---
# Core Deployment with TLS
apiVersion: apps/v1
kind: Deployment
metadata:
  name: taranis-core
spec:
  replicas: 1
  selector:
    matchLabels:
      app: taranis-core
  template:
    metadata:
      labels:
        app: taranis-core
    spec:
      containers:
      - name: core
        image: ghcr.io/taranis-ai/taranis-core:latest
        env:
        - name: GRANIAN_SSL_CERTIFICATE
          value: "/certs/tls.crt"
        - name: GRANIAN_SSL_KEYFILE
          value: "/certs/tls.key"
        - name: TARANIS_CORE_URL
          value: "https://your-domain.com/api"
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: taranis-secrets
              key: api-key
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: taranis-secrets
              key: jwt-secret
        volumeMounts:
        - name: tls-certs
          mountPath: /certs
          readOnly: true
      volumes:
      - name: tls-certs
        secret:
          secretName: taranis-tls
```
